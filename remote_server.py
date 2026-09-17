"""
remote_server.py - Sonance Wi-Fi Mobile Remote Controller & Cast Server

Part of the Sonance project (https://github.com/Sandeep2062/Sonance)
Copyright (C) 2024-2026 Sandeep Khadka — GPLv3 with Commons Clause

Embedded zero-dependency HTTP & SSE server allowing users to control desktop
playback, queue, volume, and watch real-time synchronized scrolling lyrics
from any mobile phone or tablet on the same local Wi-Fi network.
"""

import http.server
import json
import os
import socket
import socketserver
import threading
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional


def get_local_ip() -> str:
    """Discovers the machine's primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


# Mobile Web Controller HTML (Self-Contained Responsive Glassmorphic UI)
MOBILE_REMOTE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Sonance Mobile Remote</title>
<style>
  :root {
    --bg: #090d16;
    --card: rgba(25, 33, 50, 0.7);
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.35);
    --text: #f8fafc;
    --text-dim: #94a3b8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
  body {
    background: radial-gradient(circle at top, #1e1b4b 0%, var(--bg) 70%);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 16px;
    user-select: none;
    overflow-x: hidden;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 1.1rem; color: var(--accent); }
  .status-badge { font-size: 0.75rem; background: rgba(56,189,248,0.15); border: 1px solid var(--accent); color: var(--accent); padding: 3px 8px; border-radius: 999px; }
  
  .player-card {
    background: var(--card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 20px;
    margin-top: 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: 0 12px 32px rgba(0,0,0,0.5);
  }
  .cover-box {
    width: 170px;
    height: 170px;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6), 0 0 20px var(--accent-glow);
    background: #111;
  }
  .cover-box img { width: 100%; height: 100%; object-fit: cover; }
  .track-info { text-align: center; margin-bottom: 14px; width: 100%; }
  .track-title { font-size: 1.25rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .track-artist { font-size: 0.95rem; color: var(--text-dim); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  
  .lyrics-box {
    width: 100%;
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }
  .lyrics-line { font-size: 0.95rem; font-weight: 600; color: #38bdf8; text-shadow: 0 0 12px rgba(56,189,248,0.5); transition: all 0.2s; }
  
  .time-bar { width: 100%; margin-bottom: 16px; }
  .progress-slider {
    width: 100%;
    -webkit-appearance: none;
    height: 6px;
    border-radius: 3px;
    background: rgba(255,255,255,0.15);
    outline: none;
  }
  .progress-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    cursor: pointer;
  }
  .time-labels { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-dim); margin-top: 4px; }
  
  .controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    width: 100%;
    margin-bottom: 16px;
  }
  .btn-ctrl {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    color: var(--text);
    width: 46px;
    height: 46px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    cursor: pointer;
    transition: transform 0.1s, background 0.2s;
  }
  .btn-ctrl:active { transform: scale(0.92); background: rgba(255,255,255,0.2); }
  .btn-play {
    width: 60px;
    height: 60px;
    background: var(--accent);
    color: #000;
    font-size: 1.6rem;
    box-shadow: 0 0 20px var(--accent-glow);
  }
  
  .volume-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 0 8px;
  }
  .volume-slider {
    flex: 1;
    -webkit-appearance: none;
    height: 5px;
    border-radius: 3px;
    background: rgba(255,255,255,0.15);
    outline: none;
  }
  .volume-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--text);
    cursor: pointer;
  }
  
  .queue-section {
    margin-top: 16px;
    flex: 1;
    overflow-y: auto;
  }
  .queue-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim); margin-bottom: 8px; }
  .queue-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    margin-bottom: 6px;
    font-size: 0.85rem;
  }
  .queue-item.active { border-color: var(--accent); background: rgba(56,189,248,0.1); color: var(--accent); }
</style>
</head>
<body>
<header>
  <div class="brand"><span>🎵</span> Sonance Remote</div>
  <div class="status-badge" id="connStatus">Connected</div>
</header>

<div class="player-card">
  <div class="cover-box">
    <img id="coverImg" src="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300" alt="Cover">
  </div>
  <div class="track-info">
    <div class="track-title" id="trackTitle">No Track Playing</div>
    <div class="track-artist" id="trackArtist">Sonance Desktop</div>
  </div>
  
  <div class="lyrics-box">
    <div class="lyrics-line" id="lyricsLine">♪ Real-time lyrics will sync here ♪</div>
  </div>
  
  <div class="time-bar">
    <input type="range" class="progress-slider" id="progressSlider" min="0" max="100" value="0">
    <div class="time-labels">
      <span id="currTime">0:00</span>
      <span id="totalTime">0:00</span>
    </div>
  </div>
  
  <div class="controls">
    <button class="btn-ctrl" onclick="sendAction('prev')">⏮</button>
    <button class="btn-ctrl btn-play" id="playBtn" onclick="sendAction('play_pause')">▶</button>
    <button class="btn-ctrl" onclick="sendAction('next')">⏭</button>
  </div>
  
  <div class="volume-bar">
    <span>🔈</span>
    <input type="range" class="volume-slider" id="volumeSlider" min="0" max="100" value="80" oninput="sendAction('volume', this.value / 100)">
    <span>🔊</span>
  </div>
</div>

<div class="queue-section">
  <div class="queue-title">Up Next in Queue</div>
  <div id="queueList"></div>
</div>

<script>
  let isSeeking = false;
  
  function formatTime(secs) {
    if (isNaN(secs) || secs < 0) return "0:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }
  
  async function sendAction(action, value = null) {
    try {
      await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, value })
      });
    } catch(e) {
      console.error(e);
    }
  }
  
  document.getElementById('progressSlider').addEventListener('mousedown', () => isSeeking = true);
  document.getElementById('progressSlider').addEventListener('touchstart', () => isSeeking = true);
  document.getElementById('progressSlider').addEventListener('change', (e) => {
    isSeeking = false;
    sendAction('seek', parseFloat(e.target.value));
  });
  
  function updateUI(data) {
    if (!data) return;
    document.getElementById('trackTitle').textContent = data.title || "No Track Playing";
    document.getElementById('trackArtist').textContent = data.artist || "Sonance Desktop";
    if (data.cover_url) {
      document.getElementById('coverImg').src = data.cover_url;
    }
    document.getElementById('playBtn').textContent = data.is_playing ? '⏸' : '▶';
    
    if (data.current_lyric) {
      document.getElementById('lyricsLine').textContent = data.current_lyric;
    }
    
    if (!isSeeking && data.duration > 0) {
      const slider = document.getElementById('progressSlider');
      slider.max = data.duration;
      slider.value = data.position || 0;
      document.getElementById('currTime').textContent = formatTime(data.position || 0);
      document.getElementById('totalTime').textContent = formatTime(data.duration || 0);
    }
    
    if (data.volume !== undefined) {
      document.getElementById('volumeSlider').value = Math.round(data.volume * 100);
    }
    
    // Render Queue
    if (Array.isArray(data.queue)) {
      const qList = document.getElementById('queueList');
      qList.innerHTML = data.queue.map((t, idx) => `
        <div class="queue-item ${idx === data.current_index ? 'active' : ''}" onclick="sendAction('play_index', ${idx})">
          <div><strong>${t.title || 'Untitled'}</strong><br><small style="color:var(--text-dim)">${t.artist || 'Unknown'}</small></div>
          <div>${formatTime(t.duration || 0)}</div>
        </div>
      `).join('');
    }
  }
  
  // SSE or Polling
  function startSync() {
    const poll = async () => {
      try {
        const res = await fetch('/api/state');
        if (res.ok) {
          const data = await res.json();
          updateUI(data);
          document.getElementById('connStatus').textContent = 'Connected';
          document.getElementById('connStatus').style.color = 'var(--accent)';
        }
      } catch (err) {
        document.getElementById('connStatus').textContent = 'Offline';
        document.getElementById('connStatus').style.color = '#f43f5e';
      }
    };
    setInterval(poll, 800);
    poll();
  }
  
  startSync();
</script>
</body>
</html>
"""


class RemoteState:
    """Thread-safe playback state store for remote clients."""
    def __init__(self):
        self._lock = threading.Lock()
        self.state: Dict[str, Any] = {
            "is_playing": False,
            "title": "Welcome to Sonance",
            "artist": "Sonance Desktop",
            "album": "",
            "cover_url": "",
            "duration": 0,
            "position": 0,
            "volume": 0.8,
            "current_lyric": "♪ Ready to stream & sync ♪",
            "current_index": 0,
            "queue": []
        }
        self.action_handler: Optional[Callable[[str, Any], None]] = None

    def update(self, new_data: Dict[str, Any]):
        with self._lock:
            self.state.update(new_data)

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.state)


global_remote_state = RemoteState()


class RemoteRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default console spam
        pass

    def do_GET(self):
        url_path = urllib.parse.urlparse(self.path).path
        if url_path in ("/", "/remote", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(MOBILE_REMOTE_HTML.encode("utf-8"))
        elif url_path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps(global_remote_state.get())
            self.wfile.write(data.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url_path = urllib.parse.urlparse(self.path).path
        if url_path == "/api/action":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8")
                payload = json.loads(body)
                action = payload.get("action")
                value = payload.get("value")

                if global_remote_state.action_handler and action:
                    global_remote_state.action_handler(action, value)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"success":true}')
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def generate_qr_svg(url: str) -> str:
    """Generates an SVG representation of a QR code for the given URL."""
    try:
        import qrcode
        import qrcode.image.svg
        import io
        qr = qrcode.QRCode(
            version=1,
            box_size=8,
            border=2,
            image_factory=qrcode.image.svg.SvgPathImage
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#000000", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception:
        return ""


class RemoteServer:
    def __init__(self, port: int = 5050):
        self.port = port
        self.httpd: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False
        self.local_ip = get_local_ip()

    def start(self) -> Dict[str, Any]:
        if self.is_running:
            url = f"http://{self.local_ip}:{self.port}"
            return {
                "success": True,
                "running": True,
                "url": url,
                "ip": self.local_ip,
                "port": self.port,
                "qr_svg": generate_qr_svg(url)
            }

        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True

        for p in range(self.port, self.port + 10):
            try:
                self.httpd = ReusableTCPServer(("0.0.0.0", p), RemoteRequestHandler)
                self.port = p
                break
            except Exception:
                continue

        if not self.httpd:
            return {"success": False, "error": "Could not bind to local port"}

        self.is_running = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

        url = f"http://{self.local_ip}:{self.port}"
        return {
            "success": True,
            "running": True,
            "url": url,
            "ip": self.local_ip,
            "port": self.port,
            "qr_svg": generate_qr_svg(url)
        }

    def stop(self) -> Dict[str, Any]:
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
        self.is_running = False
        return {"success": True, "running": False}

    def get_info(self) -> Dict[str, Any]:
        url = f"http://{self.local_ip}:{self.port}" if self.is_running else ""
        return {
            "running": self.is_running,
            "url": url,
            "ip": self.local_ip,
            "port": self.port,
            "qr_svg": generate_qr_svg(url) if url else ""
        }


# Global instance
remote_server = RemoteServer()
