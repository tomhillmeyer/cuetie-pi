# Testing Guide

This document covers running Cutie Pi in development and testing the Phase 1 functionality.

---

## Prerequisites

### On Your Development Machine (macOS)

Install the required tools:

```bash
# Install Python, Node, and mpv
brew install python@3.11 node mpv
```

### On Raspberry Pi or Ubuntu Server

A fresh install of Pi OS Lite or Ubuntu Server does NOT include Python 3.11+ or Node 18+. Install them first:

**Ubuntu Server:**
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv curl
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo apt install -y mpv
```

**Raspberry Pi OS Lite (Bookworm):**
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv curl
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo apt install -y mpv
```

For headless setups (no desktop), mpv will need extra flags — see "Platform-Specific Notes" below.

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

## Testing Phase 1 Functionality

### 1. Upload Media

1. Open **http://localhost:5173** in your browser
2. Drag and drop a media file (`.jpg`, `.png`, `.gif`, `.mp4`, `.mov`, `.webm`) onto the drop zone
3. Or click "Browse" to select files

**Expected:** The file appears in the cue list below with a play button and delete button.

### 2. Reorder Cues

1. Grab the handle (☰) on any cue
2. Drag it to a new position

**Expected:** The cue order updates immediately and persists to `cues.json`.

### 3. Play a Cue

1. Click the play button (▶) on any cue

**Expected:**
- On macOS: mpv opens in a window and plays the media fullscreen
- On Pi/NUC with desktop: mpv plays fullscreen on the connected display

### 4. Stop Playback

1. Click "Stop Playback" button at the bottom

**Expected:** mpv closes and playback stops.

### 5. Delete a Cue

1. Click the delete button (🗑) on any cue

**Expected:** The cue is removed from the list and the media file is deleted from `media/`.

### 6. Test the API Directly

```bash
# List all cues
curl http://localhost:8000/api/cues

# Get playback status
curl http://localhost:8000/api/status

# Stop playback
curl -X POST http://localhost:8000/api/stop
```

---

## Platform-Specific Notes

### macOS

- Works out of the box
- mpv opens in a window (not true fullscreen, but fine for development)
- `DISPLAY` can be left unset in `.env`

### Raspberry Pi 4/5 (with desktop)

- Set `DISPLAY=:0` in `.env`
- mpv plays fullscreen on the Pi's display

### Ubuntu Server (headless, no desktop)

Two options:

**Option A: Minimal desktop (recommended for Phase 1)**
```bash
sudo apt install --no-install-recommends xorg openbox
```
Then set `DISPLAY=:0` and start the desktop before running mpv.

**Option B: DRM directly (no display server)**
This requires mpv to be built with DRM support. The player code will need modification in a future phase to support `--vo=drm` instead of `--fullscreen`.

---

## File Locations

| File | Purpose |
|------|---------|
| `backend/cues.json` | Persisted cue list (JSON) |
| `backend/media/` | Uploaded media files |

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

### Video doesn't display (headless Linux)

- You need a display server (desktop environment) or DRM output
- See "Platform-Specific Notes" above

---

## Next Steps (Phase 2)

Once Phase 1 is working, Phase 2 adds:

- **GO button** — advance to and play the next cue
- **Reset button** — reset cue pointer without playing
- Index-based triggers: `POST /api/go`, `POST /api/go/{n}`
- REST API for external tools (QLab, curl)

See `build-spec.md` for full Phase 2 specification.