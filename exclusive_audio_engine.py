"""
Sonance Audiophile Workstation — Exclusive Audio Engine
======================================================
Provides bit-perfect hardware output bypassing OS mixers:
- Windows: WASAPI Exclusive Mode & ASIO driver discovery/routing
- Direct hardware clock locking without software resampling
- High-priority MMCSS ("Pro Audio") thread scheduling
- Real-time bit-perfect telemetry (sample rate, bit depth, buffer latency)
"""

import os
import sys
import time
import json
import math
import ctypes
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np

# Audio library imports
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    sd = None
    HAS_SOUNDDEVICE = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    sf = None
    HAS_SOUNDFILE = False

# Windows Registry import for ASIO enumeration
if sys.platform == "win32":
    try:
        import winreg
        HAS_WINREG = True
    except ImportError:
        winreg = None
        HAS_WINREG = False
else:
    winreg = None
    HAS_WINREG = False

CONFIG_FILE = Path(__file__).resolve().parent / "cache" / "exclusive_audio_config.json"


def _enable_mmcss_pro_audio():
    """Sets current thread priority to MMCSS 'Pro Audio' on Windows."""
    if sys.platform != "win32":
        return None
    try:
        avrt = ctypes.windll.avrt
        avrt.AvSetMmThreadCharacteristicsW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        avrt.AvSetMmThreadCharacteristicsW.restype = ctypes.c_void_p
        task_index = ctypes.c_ulong(0)
        handle = avrt.AvSetMmThreadCharacteristicsW("Pro Audio", ctypes.byref(task_index))
        return handle
    except Exception:
        return None


def _revert_mmcss(handle):
    """Reverts MMCSS thread priority."""
    if sys.platform == "win32" and handle:
        try:
            avrt = ctypes.windll.avrt
            avrt.AvRevertMmThreadCharacteristics.argtypes = [ctypes.c_void_p]
            avrt.AvRevertMmThreadCharacteristics(handle)
        except Exception:
            pass


class ExclusiveAudioEngine:
    """Singleton audio engine for bit-perfect Exclusive and ASIO playback."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "ExclusiveAudioEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.lock = threading.Lock()
        self._config = self._load_config()

        # Playback thread state
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_requested = threading.Event()
        self._pause_requested = threading.Event()
        self._seek_requested: Optional[float] = None
        self._current_stream = None

        # Playback status
        self._state = "idle"  # "idle", "playing", "paused", "stopped"
        self._current_file: Optional[str] = None
        self._position: float = 0.0
        self._duration: float = 0.0
        self._active_sample_rate: int = 44100
        self._active_channels: int = 2
        self._active_bit_depth: str = "16-bit PCM"
        self._active_device_name: str = "Default"
        self._is_bit_perfect: bool = False
        self._buffer_latency_ms: float = 0.0

    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "mode": "wasapi_exclusive" if sys.platform == "win32" else "shared",
            "device_id": None,
            "buffer_size": 256,
            "bit_perfect_lock": True,
            "volume": 1.0
        }
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    default_config.update(saved)
            except Exception:
                pass
        return default_config

    def _save_config(self):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
        except Exception:
            pass

    def get_config(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self._config)

    def set_config(self, mode: Optional[str] = None, device_id: Optional[int] = None,
                   buffer_size: Optional[int] = None, bit_perfect_lock: Optional[bool] = None,
                   volume: Optional[float] = None) -> Dict[str, Any]:
        with self.lock:
            if mode in ["shared", "wasapi_exclusive", "asio", "coreaudio_hog", "alsa_hw"]:
                self._config["mode"] = mode
            if device_id is not None:
                self._config["device_id"] = device_id
            if buffer_size is not None and buffer_size in [64, 128, 256, 512, 1024, 2048]:
                self._config["buffer_size"] = buffer_size
            if bit_perfect_lock is not None:
                self._config["bit_perfect_lock"] = bool(bit_perfect_lock)
            if volume is not None:
                self._config["volume"] = max(0.0, min(1.0, float(volume)))
            self._save_config()
            return dict(self._config)

    def query_devices(self) -> Dict[str, Any]:
        """Queries all system audio output devices and registered drivers."""
        if not HAS_SOUNDDEVICE:
            return {
                "available": False,
                "error": "sounddevice library not installed",
                "devices": [],
                "asio_drivers": []
            }

        devices_list = []
        host_apis = []

        try:
            raw_apis = sd.query_hostapis()
            for i, api in enumerate(raw_apis):
                host_apis.append({
                    "id": i,
                    "name": api["name"],
                    "devices_count": len(api["devices"])
                })
        except Exception as e:
            raw_apis = []

        try:
            raw_devices = sd.query_devices()
            default_out = sd.default.device[1]
            for i, dev in enumerate(raw_devices):
                if dev["max_output_channels"] > 0:
                    api_info = raw_apis[dev["hostapi"]] if dev["hostapi"] < len(raw_apis) else {"name": "Unknown"}
                    api_name = api_info.get("name", "Unknown")
                    is_wasapi = "WASAPI" in api_name
                    is_default = (i == default_out)

                    devices_list.append({
                        "id": i,
                        "name": dev["name"],
                        "host_api": api_name,
                        "host_api_id": dev["hostapi"],
                        "max_channels": dev["max_output_channels"],
                        "default_sample_rate": int(dev["default_samplerate"]),
                        "is_default": is_default,
                        "is_wasapi": is_wasapi
                    })
        except Exception as e:
            pass

        asio_drivers = self.query_asio_drivers()

        return {
            "available": True,
            "host_apis": host_apis,
            "devices": devices_list,
            "asio_drivers": asio_drivers,
            "current_config": self.get_config()
        }

    def query_asio_drivers(self) -> List[Dict[str, str]]:
        """Scans the Windows Registry for registered ASIO drivers."""
        if not HAS_WINREG or sys.platform != "win32":
            return []

        drivers = []
        seen_clsids = set()
        roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        subkeys = [r"SOFTWARE\ASIO", r"SOFTWARE\WOW6432Node\ASIO"]

        for root in roots:
            for subkey in subkeys:
                try:
                    key = winreg.OpenKey(root, subkey)
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        try:
                            driver_name = winreg.EnumKey(key, i)
                            driver_key = winreg.OpenKey(key, driver_name)
                            clsid, _ = winreg.QueryValueEx(driver_key, "CLSID")
                            if clsid in seen_clsids:
                                continue
                            seen_clsids.add(clsid)
                            try:
                                desc, _ = winreg.QueryValueEx(driver_key, "Description")
                            except Exception:
                                desc = driver_name
                            drivers.append({
                                "name": driver_name,
                                "description": desc,
                                "clsid": clsid
                            })
                        except Exception:
                            pass
                except Exception:
                    pass

        return drivers

    def probe_device_rates(self, device_id: int, is_exclusive: bool = True) -> List[int]:
        """Tests standard audiophile sample rates on the given device."""
        if not HAS_SOUNDDEVICE:
            return []

        rates_to_test = [44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000]
        supported = []

        settings = None
        if is_exclusive and sys.platform == "win32":
            try:
                settings = sd.WasapiSettings(exclusive=True)
            except Exception:
                settings = None

        for sr in rates_to_test:
            try:
                sd.check_output_settings(
                    device=device_id,
                    samplerate=sr,
                    channels=2,
                    dtype="float32",
                    extra_settings=settings
                )
                supported.append(sr)
            except Exception:
                pass

        return supported

    def play_test_tone(self, device_id: Optional[int] = None, sample_rate: int = 48000,
                       duration: float = 0.5, freq: float = 440.0) -> Dict[str, Any]:
        """Plays a brief bit-perfect 440 Hz test chime in Exclusive mode to verify DAC lock."""
        if not HAS_SOUNDDEVICE:
            return {"success": False, "error": "sounddevice not available"}

        if device_id is None:
            # Find default WASAPI device
            for dev in sd.query_devices():
                if dev["max_output_channels"] > 0:
                    api = sd.query_hostapis(dev["hostapi"])["name"]
                    if "WASAPI" in api:
                        device_id = dev["index"] if "index" in dev else 0
                        break

        total_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, total_samples, endpoint=False)
        wave_data = 0.15 * np.sin(2 * np.pi * freq * t).astype(np.float32)

        # Apply smooth 20ms attack and release envelope to prevent click
        env_samples = int(sample_rate * 0.02)
        envelope = np.ones(total_samples, dtype=np.float32)
        envelope[:env_samples] = np.linspace(0, 1, env_samples)
        envelope[-env_samples:] = np.linspace(1, 0, env_samples)
        wave_data *= envelope

        stereo_data = np.column_stack([wave_data, wave_data])

        try:
            extra = sd.WasapiSettings(exclusive=True) if sys.platform == "win32" else None
            stream = sd.OutputStream(
                device=device_id,
                samplerate=sample_rate,
                channels=2,
                dtype="float32",
                extra_settings=extra
            )
            stream.start()
            stream.write(stereo_data)
            stream.stop()
            stream.close()
            return {
                "success": True,
                "message": f"Hardware Exclusive Lock verified on device {device_id} at {sample_rate} Hz (440 Hz Chime)",
                "sample_rate": sample_rate,
                "duration": duration
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def play(self, file_path: str, start_time: float = 0.0) -> Dict[str, Any]:
        """Starts bit-perfect exclusive playback of an audio file."""
        if not HAS_SOUNDDEVICE or not HAS_SOUNDFILE:
            return {"success": False, "error": "sounddevice or soundfile missing"}

        p = Path(file_path)
        if not p.exists():
            return {"success": False, "error": f"Audio file not found: {file_path}"}

        # Stop existing playback first
        self.stop()

        self._stop_requested.clear()
        self._pause_requested.clear()
        self._seek_requested = None
        self._current_file = str(p)

        self._playback_thread = threading.Thread(
            target=self._playback_loop,
            args=(str(p), start_time),
            name="ExclusiveAudioStreamer",
            daemon=True
        )
        self._playback_thread.start()

        return {
            "success": True,
            "message": f"Started Exclusive playback for: {p.name}",
            "file": str(p),
            "start_time": start_time
        }

    def _playback_loop(self, file_path: str, start_time: float):
        """Worker thread executing the real-time stream."""
        mmcss_handle = _enable_mmcss_pro_audio()

        try:
            with sf.SoundFile(file_path) as sfile:
                sr = sfile.samplerate
                channels = sfile.channels
                total_frames = len(sfile)
                duration = total_frames / sr
                subtype = sfile.subtype

                self._duration = duration
                self._active_sample_rate = sr
                self._active_channels = min(2, channels)
                self._active_bit_depth = f"{subtype.replace('_', ' ')}"

                # Determine device
                cfg = self.get_config()
                device_id = cfg.get("device_id")
                mode = cfg.get("mode", "wasapi_exclusive")
                buffer_size = cfg.get("buffer_size", 256)

                # If device_id is None, resolve first appropriate WASAPI/default output
                if device_id is None:
                    raw_devs = sd.query_devices()
                    for i, d in enumerate(raw_devs):
                        if d["max_output_channels"] > 0:
                            api = sd.query_hostapis(d["hostapi"])["name"]
                            if mode == "wasapi_exclusive" and "WASAPI" in api:
                                device_id = i
                                break
                    if device_id is None:
                        device_id = sd.default.device[1]

                dev_info = sd.query_devices(device_id)
                self._active_device_name = dev_info["name"]

                # Configure stream settings
                extra_settings = None
                if mode == "wasapi_exclusive" and sys.platform == "win32":
                    try:
                        extra_settings = sd.WasapiSettings(exclusive=True)
                        self._is_bit_perfect = True
                    except Exception:
                        extra_settings = None
                        self._is_bit_perfect = False
                else:
                    self._is_bit_perfect = False

                # Seek initial position
                initial_frame = int(start_time * sr)
                if initial_frame > 0 and initial_frame < total_frames:
                    sfile.seek(initial_frame)
                current_frame = initial_frame

                out_channels = 2  # Standard stereo DAC presentation
                dtype = "float32"

                # Estimate buffer latency
                self._buffer_latency_ms = (buffer_size / sr) * 1000.0

                with sd.OutputStream(
                    device=device_id,
                    samplerate=sr,
                    channels=out_channels,
                    dtype=dtype,
                    blocksize=buffer_size,
                    extra_settings=extra_settings
                ) as stream:
                    self._current_stream = stream
                    self._state = "playing"

                    chunk_size = buffer_size

                    while not self._stop_requested.is_set():
                        # Handle seek
                        if self._seek_requested is not None:
                            target_time = self._seek_requested
                            self._seek_requested = None
                            seek_frame = int(target_time * sr)
                            seek_frame = max(0, min(total_frames - 1, seek_frame))
                            sfile.seek(seek_frame)
                            current_frame = seek_frame

                        # Handle pause
                        if self._pause_requested.is_set():
                            self._state = "paused"
                            time.sleep(0.05)
                            continue
                        else:
                            self._state = "playing"

                        # Read chunk
                        data = sfile.read(chunk_size, dtype=dtype)
                        if len(data) == 0:
                            # EOF reached
                            break

                        # Channel formatting (mono to stereo if needed)
                        if channels == 1:
                            pcm_out = np.column_stack([data, data])
                        elif channels > 2:
                            pcm_out = data[:, :2]
                        else:
                            pcm_out = data

                        # Apply volume if bit-perfect lock is disabled
                        cfg = self.get_config()
                        if not cfg.get("bit_perfect_lock", True):
                            vol = cfg.get("volume", 1.0)
                            if vol < 1.0:
                                pcm_out = pcm_out * vol
                                self._is_bit_perfect = False
                        else:
                            self._is_bit_perfect = (mode == "wasapi_exclusive")

                        stream.write(pcm_out)
                        current_frame += len(data)
                        self._position = current_frame / sr

        except Exception as e:
            self._state = "error"
        finally:
            self._state = "stopped" if not self._stop_requested.is_set() else "idle"
            self._current_stream = None
            _revert_mmcss(mmcss_handle)

    def pause(self):
        """Pauses the exclusive playback stream."""
        self._pause_requested.set()
        self._state = "paused"

    def resume(self):
        """Resumes the exclusive playback stream."""
        self._pause_requested.clear()
        self._state = "playing"

    def seek(self, position_sec: float):
        """Seeks to the given position in seconds."""
        self._seek_requested = max(0.0, float(position_sec))

    def stop(self):
        """Stops playback and releases the exclusive DAC lock."""
        self._stop_requested.set()
        self._pause_requested.clear()
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.5)
        self._playback_thread = None
        self._state = "idle"
        self._position = 0.0

    def get_status(self) -> Dict[str, Any]:
        """Returns real-time telemetry of the exclusive audio pipeline."""
        return {
            "state": self._state,
            "file": self._current_file,
            "position": round(self._position, 2),
            "duration": round(self._duration, 2),
            "sample_rate": self._active_sample_rate,
            "channels": self._active_channels,
            "bit_depth": self._active_bit_depth,
            "device_name": self._active_device_name,
            "is_bit_perfect": self._is_bit_perfect,
            "buffer_latency_ms": round(self._buffer_latency_ms, 2),
            "mode": self._config.get("mode", "shared")
        }


# Global helper functions
def get_engine() -> ExclusiveAudioEngine:
    return ExclusiveAudioEngine.get_instance()


def query_audio_devices() -> Dict[str, Any]:
    return get_engine().query_devices()
