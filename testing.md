# Testing Guide

This document covers running Cutie Pi in development and testing functionality.

**Note**: Both Phase 1 (Web UI) and Phase 2 (REST API) are fully implemented.

---

## Prerequisites

### On Your Development Machine (macOS)

Install the required tools:

```bash
# Install Python, Node, and mpv
brew install python@3.11 node mpv sshpass
```

### On Raspberry Pi or Ubuntu Server

Use the `provision-pi.sh` script for first-time setup:

```bash
PI_HOST=192.168.1.100 ./provision-pi.sh
```

---

## Running the Application

### Start the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

The API is now available at **http://localhost:8000**. FastAPI docs are at **http://localhost:8000/docs**.

### Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI is now available at **http://localhost:5173**.

---

## Testing Phase 1 (Web UI) Functionality

### 1. Upload Media

1. Open **http://localhost:5173** in your browser
2. Drag and drop a media file (`.jpg`, `.png`, `.gif`, `.mp4`, `.mov`, `.webm`) onto the drop zone
3. Or click "Browse" to select files

**Expected**: The file appears in the cue list below with a play button and delete button.

### 2. Reorder Cues

1. Grab the handle (☰) on any cue
2. Drag it to a new position

**Expected**: The cue order updates immediately and persists to `cues.json`.

### 3. Play a Cue

1. Click the play button (▶) on any cue

**Expected**:
- On macOS: mpv opens in a window and plays the media
- On Pi/NUC with DRM: mpv plays fullscreen on the connected display

### 4. Stop Playback

1. Click "Stop" button at the top

**Expected**: Display shows black (black.png), playback stops.

### 5. Delete a Cue

1. Click the delete button (🗑) on any cue

**Expected**: The cue is removed from the list and the media file is deleted from `media/`.

---

## Testing Phase 2 (REST API) Functionality

### Test Endpoints Directly

```bash
# List all cues
curl http://localhost:8000/api/cues

# Get playback status
curl http://localhost:8000/api/status

# Get detailed stats
curl http://localhost:8000/api/stats

# Get debug info (mpv startup logs, etc.)
curl http://localhost:8000/api/debug
```

### Test Index-based Triggering

```bash
# Reset pointer to beginning (before cue 1)
curl -X POST http://localhost:8000/api/reset

# Play next cue (GO)
curl -X POST http://localhost:8000/api/go

# Play cue #2 (1-based)
curl -X POST http://localhost:8000/api/go/2

# Play previous cue
curl -X POST http://localhost:8000/api/previous

# Stop playback
curl -X POST http://localhost:8000/api/stop

# Get current pointer position
curl http://localhost:8000/api/current
```

### Test Keyboard Hardware Control

On a Raspberry Pi with a USB keyboard:
- Press **Right arrow** → Should trigger GO (next cue)
- Press **Left arrow** → Should trigger PREVIOUS

---

## Platform-Specific Notes

### macOS

- Works out of the box
- mpv opens in a window (not true fullscreen, but fine for development)
- `DISPLAY` can be left unset in `.env`

### Raspberry Pi 4/5 (Weston/Wayland)

Uses Weston Wayland compositor for reliable display output (solves PNG-to-PNG image switching issues seen under raw DRM).

**Requirements**:
- Pi OS Lite (64-bit) recommended
- `weston` and `seatd` packages installed
- User in `video`, `render`, and `tty` groups
- `gpu_mem=256` in `/boot/firmware/config.txt`
- Weston systemd service starts before cuetie-pi
- `SupplementaryGroups=video render` in systemd service

**mpv flags used**:
```
--vo=gpu
--gpu-context=wayland
--gpu-api=opengl
--opengl-es=yes
--gpu-dumb-mode=yes
--hwdec=drm-copy
```

**Environment variables for Wayland** (set by systemd service, or manually):
```
WAYLAND_DISPLAY=wayland-1
XDG_RUNTIME_DIR=/tmp/weston-runtime
```

### Ubuntu Server (headless, no desktop)

Similar to Raspberry Pi. Install `weston` and `seatd`, configure as described above.

---

## File Locations

| File | Purpose |
|------|---------|
| `backend/cues.json` | Persisted cue list (JSON) |
| `backend/media/` | Uploaded media files |
| `backend/.env` | Environment variables |

To inspect the cue list:
```bash
cat backend/cues.json
```

---

## Troubleshooting

### "Cannot connect to backend"

- Make sure the backend is running on port 8000
- Check the terminal for errors
- Try `curl http://localhost:8000/api/cues` to test connectivity

### "mpv not found"

```bash
# macOS
brew install mpv

# Ubuntu/Pi OS
sudo apt install mpv
```

### Upload fails

- Check that `backend/media/` directory exists and is writable
- Check terminal for error messages

### Video/Image doesn't display (headless Linux/Weston)

#### Common Causes:

1. **Weston not running** - Check `systemctl status weston`
2. **User not in groups** - `pi` user needs `video`, `render`, and `tty` groups
3. **systemd missing groups** - Service needs `SupplementaryGroups=video render`
4. **GPU memory too low** - Need `gpu_mem=256`
5. **Wayland socket mismatch** - `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` must match between weston and cuetie-pi services

#### Debug Steps:

```bash
# Check groups
groups pi

# Check that Weston is running
systemctl status weston

# Check Weston logs
journalctl -u weston -f

# Check if mpv works via Weston (run in weston's XDG_RUNTIME_DIR)
sudo -u pi XDG_RUNTIME_DIR=/tmp/weston-runtime mpv --vo=gpu --gpu-context=wayland /path/to/video.mp4

# Check service logs
journalctl -u cuetie-pi -f

# Check API debug endpoint
curl http://pi-ip:8000/api/debug
```

### PNG-to-PNG Image Switching

This was the original motivation for migrating from DRM to Weston. The issue is now fixed — Weston's compositor properly handles buffer swaps even when consecutive images have identical dimensions.

### Service Won't Start

```bash
# Check service status
sudo systemctl status cuetie-pi

# Check logs
journalctl -u cuetie-pi

# Common issues:
# 1. venv doesn't exist at /home/pi/cuetie-pi/backend/venv/
# 2. Wrong WorkingDirectory in service file
# 3. Missing SupplementaryGroups=video render
```

---

## Deploy Testing

### Test deploy.sh

```bash
# Deploy current code to Pi
PI_HOST=192.168.1.100 ./deploy.sh
```

**Expected**:
1. Frontend builds
2. Code syncs to Pi (preserving media, cues, .env)
3. Service restarts
4. Service verifies as `active`

### Test provision-pi.sh

For first-time setup or failed installations:

```bash
PI_HOST=192.168.1.100 ./provision-pi.sh
```

**Expected**:
1. System packages installed
2. User added to `video`/`render` groups
3. GPU memory checked (`gpu_mem=256`)
4. Python venv created and dependencies installed
5. Systemd service installed and started

---

## Useful Commands

### On the Pi

```bash
# View service logs
journalctl -u cuetie-pi -f

# Restart service
sudo systemctl restart cuetie-pi

# Check service status
sudo systemctl status cuetie-pi

# Check groups
groups pi

# Check mpv version
mpv --version
```

### Local Development

```bash
# Test API
curl http://localhost:8000/api/status

# Test specific API endpoints
curl -X POST http://localhost:8000/api/go
curl -X POST http://localhost:8000/api/stop
```
