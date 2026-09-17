"""
discord_rpc.py - Sonance Discord Rich Presence (RPC) Integration

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Connects to local Discord IPC socket to display live song title, artist, album,
duration timer, and interactive buttons on user Discord profile.
"""

import os
import sys
import json
import time
import socket
import struct
import threading
from typing import Optional, Dict, Any

CLIENT_ID = "1280000000000000000"  # Default Sonance Discord Client ID


class DiscordRPC:
  def __init__(self, client_id: str = CLIENT_ID):
    self.client_id = client_id
    self._sock = None
    self._connected = False
    self._lock = threading.Lock()
    self._current_activity = None

  def connect(self) -> bool:
    """Attempts to connect to Discord local IPC socket."""
    if self._connected:
      return True

    for i in range(10):
      try:
        if sys.platform == "win32":
          pipe_path = rf"\\.\pipe\discord-ipc-{i}"
          self._sock = open(pipe_path, "w+b")
        else:
          ipc_path = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
          pipe_path = os.path.join(ipc_path, f"discord-ipc-{i}")
          self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
          self._sock.connect(pipe_path)

        self._connected = True
        self._handshake()
        return True
      except Exception:
        continue

    self._connected = False
    return False

  def _send(self, op: int, payload: Dict[str, Any]):
    """Sends encoded opcode and JSON payload to Discord IPC."""
    if not self._connected or not self._sock:
      return
    try:
      data = json.dumps(payload).encode("utf-8")
      header = struct.pack("<II", op, len(data))
      if sys.platform == "win32":
        self._sock.write(header + data)
        self._sock.flush()
      else:
        self._sock.sendall(header + data)
    except Exception:
      self._connected = False

  def _handshake(self):
    """Sends initial handshake with client ID."""
    self._send(0, {"v": 1, "client_id": self.client_id})

  def update_activity(
      self,
      title: str,
      artist: str,
      album: Optional[str] = None,
      duration_sec: Optional[int] = None,
      cover_url: Optional[str] = None,
      is_playing: bool = True,
  ):
    """Updates the Discord profile presence with live playing track."""
    with self._lock:
      if not self._connected:
        if not self.connect():
          return

      now = int(time.time())
      activity = {
          "details": f"{title}",
          "state": f"by {artist}",
          "assets": {
              "large_image": cover_url or "https://raw.githubusercontent.com/Sandeep2062/Sonance/main/ui/logo.png",
              "large_text": album or "Sonance Music",
              "small_image": "play" if is_playing else "pause",
              "small_text": "Playing" if is_playing else "Paused",
          },
          "buttons": [
              {"label": "Listen on Sonance", "url": "https://github.com/Sandeep2062/Sonance"},
              {"label": "Get Sonance", "url": "https://github.com/Sandeep2062/Sonance/releases"},
          ],
      }

      if is_playing and duration_sec and duration_sec > 0:
        activity["timestamps"] = {
            "start": now,
            "end": now + duration_sec,
        }

      payload = {
          "cmd": "SET_ACTIVITY",
          "args": {"pid": os.getpid(), "activity": activity},
          "nonce": str(time.time()),
      }

      self._send(1, payload)
      self._current_activity = activity

  def clear_activity(self):
    """Clears presence when music stops."""
    with self._lock:
      if self._connected:
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": None},
            "nonce": str(time.time()),
        }
        self._send(1, payload)


# Global Discord RPC manager
rpc_manager = DiscordRPC()
