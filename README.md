# Cuetie Pi

A self-hosted media playback server for Raspberry Pi. Upload images and videos through a web interface, build a cue list, and trigger playback on the device's connected display.

**Use case**: Live events, shows, church/media presentations where a simple cue-based playback system is needed.

---

## Install

Run this on your Raspberry Pi (Raspberry Pi OS Lite 64-bit recommended):

```bash
curl -fsSL https://github.com/tomhillmeyer/cuetie-pi/releases/latest/download/install.sh | bash
```

Then open `http://<pi-ip-address>:8000` in your browser.

**Requirements**:
- Raspberry Pi 4 or 5
- 64-bit OS (Raspberry Pi OS Lite recommended)
- `gpu_mem=256` in `/boot/firmware/config.txt` (set by the installer, requires reboot)
- A display connected via HDMI

The installer handles everything: installing packages, building the Python environment, configuring Weston (Wayland compositor), and setting up systemd services to start on boot.

---

## Features

### Web UI
- Drag-and-drop media upload (PNG, JPG, GIF, MP4, MOV, WEBM)
- Drag-to-reorder cue list
- Play/stop controls per cue
- Live playback stats panel (WebSocket, no polling)
- Works on any browser on the same network

### REST API
Trigger cues from external tools (QLab, `curl`, scripts):

```bash
# Play next cue
curl -X POST http://pi-ip:8000/api/go

# Play cue #3 (1-based)
curl -X POST http://pi-ip:8000/api/go/3

# Previous cue
curl -X POST http://pi-ip:8000/api/previous
```

Full API reference at [`API.md`](API.md).

### Hardware Control
- **Right arrow** → Next cue (GO)
- **Left arrow** → Previous cue

---

## How It Works

```
Browser (React)  ──WS/REST──>  FastAPI (Python)  ──IPC──>  mpv (playback)
                                     │
                                Weston Wayland Compositor
                                     │
                               Raspberry Pi Display
```

- **Backend**: Python + FastAPI on port 8000
- **Frontend**: React (Vite), served by the backend in production
- **Display**: Weston Wayland compositor renders mpv output to the HDMI display
- **Status**: Live updates via WebSocket — no polling

---

## Updating

```bash
curl -fsSL https://github.com/tomhillmeyer/cuetie-pi/releases/latest/download/install.sh | bash
```

The installer preserves your `cues.json`, uploaded media, and `.env` configuration.

---

## Local Development

**Terminal 1 — Backend**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**:
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies API and WebSocket calls to the backend.

---

## Project Structure

```
backend/
├── main.py              # FastAPI app, all routes + WebSocket
├── player.py            # mpv subprocess management
├── cues.py              # Cue list CRUD
├── keyboard.py          # Arrow key listener
├── cuetie-pi.service    # Systemd unit
├── weston.service       # Weston systemd unit
├── weston.ini           # Weston config (kiosk shell)
├── black.png            # Blank frame for stop
├── .env.example
└── requirements.txt
frontend/
├── src/
│   ├── App.jsx
│   ├── api.js           # Fetch + WebSocket helpers
│   ├── styles.css
│   └── components/
│       ├── UploadZone.jsx
│       ├── CueList.jsx
│       ├── CueItem.jsx
│       └── StatsPanel.jsx
├── dist/                # Built app
├── package.json
└── vite.config.js
```

---

## License

MIT
