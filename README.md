# Cuetie Pi

A self-hosted media playback server for Raspberry Pi and similar devices. Upload images and videos through a web interface, build a cue list, and trigger playback on the device's connected display.


---

## Quick Start

### Deploy to Raspberry Pi

```bash
# Build and deploy to your Pi
PI_HOST=192.168.1.100 ./deploy.sh
```

Then open `http://192.168.1.100:8000` in your browser.

### First-Time Pi Setup

```bash
# Full provisioning (installs packages, sets up DRM permissions, systemd)
PI_HOST=192.168.1.100 ./provision-pi.sh
```

### Local Development (macOS)

**Terminal 1 - Backend**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Features

### Web UI (Phase 1)
- Drag-and-drop media upload (PNG, JPG, GIF, MP4, MOV, WEBM)
- Drag-to-reorder cue list
- Play/stop controls
- Live playback stats panel

### REST API (Phase 2)
Trigger cues from external tools (QLab, curl, etc.):

```bash
# Play next cue
curl -X POST http://pi-ip:8000/api/go

# Play cue #3 (1-based)
curl -X POST http://pi-ip:8000/api/go/3

# Previous cue
curl -X POST http://pi-ip:8000/api/previous

# Reset pointer to beginning
curl -X POST http://pi-ip:8000/api/reset
```

### Hardware Control
- **Right arrow** → Next cue (GO)
- **Left arrow** → Previous cue

---

## Pi Requirements (DRM Headless Mode)

For the best performance without a desktop environment:

1. **User groups**: `pi` must be in `video` and `render` groups
2. **GPU memory**: `gpu_mem=256` in `/boot/firmware/config.txt`
3. **No X11/Wayland** running - it would claim the DRM device

The `provision-pi.sh` script handles this setup automatically.

---
