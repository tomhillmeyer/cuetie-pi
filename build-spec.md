# Cutie Pi — Full Build Spec (Phases 1–3)

A self-hosted media server with a browser-based GUI for uploading and playing media (images and video) on the host device's display. Designed primarily for Raspberry Pi 4/5 and Ubuntu Server on Intel NUCs, with the goal of also supporting macOS and Windows in future.

**Phases:**
- **Phase 1:** Web UI — upload media, build a cue list, trigger playback from the browser
- **Phase 2:** REST API — trigger cues by index from external tools
- **Phase 3:** OSC — trigger cues by index over UDP from show control software (QLab, etc.)

---

## Project Overview

**Cutie Pi** is a self-hosted media playback server. A user on the same local network navigates to the host device's IP address in a browser, uploads media files, and can trigger playback on the host's display from that same browser UI. The primary targets are Raspberry Pi 4/5 and Ubuntu Server running on Intel NUCs.

---

## Architecture

```
Browser (React)  <-->  FastAPI (Python)  <-->  mpv (media playback)
   :5173 (dev)            :8000                  subprocess
   or served by
   FastAPI (prod)

External Tool    --REST-->  FastAPI  (Phase 2)
(QLab, curl, etc)

External Tool    --OSC/UDP-->  OSC Listener  -->  FastAPI  (Phase 3)
(QLab, TouchOSC)    :5005
```

- **Backend:** Python + FastAPI
- **Frontend:** React (Vite), served by FastAPI in production
- **Playback:** `mpv` via Python subprocess
- **Media storage:** Local filesystem on the Pi at `./media/`
- **Cue list state:** JSON file at `./cues.json`

---

## Target Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Raspberry Pi 4 (Pi OS Bookworm 64-bit) | ✅ Primary | FKMS/KMS display stack |
| Raspberry Pi 5 (Pi OS Bookworm 64-bit) | ✅ Primary | KMS only, no legacy GL |
| Ubuntu Server 22.04/24.04 on Intel NUC | ✅ Primary | Requires display server config (see below) |
| macOS | 🔜 Future | mpv via Homebrew works; windowed mode acceptable |
| Windows | 🔜 Future | mpv via winget/scoop; out of scope for now |

Write all platform-specific code behind an abstraction so adding macOS/Windows support later is a config change, not a rewrite.

## Assumptions / Defaults

- FastAPI serves the built React app in production (single unified server on port `8000`)
- In development, Vite dev server runs on port `5173` and proxies API calls to FastAPI on `8000`
- mpv always launches **fullscreen** — this is non-negotiable for production use
- Future phases will add per-cue playback options (scale mode, rotation, etc.) stored in `cues.json`
- Supported media types: `.jpg`, `.jpeg`, `.png`, `.gif`, `.mp4`, `.mov`, `.webm`
- Only one piece of media plays at a time; triggering a new one stops the current one

---

## Repository Structure

```
cutie-pi/
├── backend/
│   ├── main.py          # FastAPI app, all routes
│   ├── player.py        # mpv subprocess management
│   ├── cues.py          # Cue list read/write helpers
│   ├── osc_server.py    # OSC listener (Phase 3)
│   ├── media/           # Uploaded media files (gitignored)
│   └── cues.json        # Cue list state (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── UploadZone.jsx     # Drag-and-drop or click-to-upload
│   │   │   ├── CueList.jsx        # Ordered list of uploaded media
│   │   │   └── CueItem.jsx        # Single cue row with play button
│   │   └── api.js                 # fetch() wrappers for all backend calls
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── .env                 # MEDIA_DIR, PORT, OSC_PORT, DISPLAY
├── .env.example         # Committed template with all keys, no values
├── requirements.txt
└── README.md
```

---

## Backend

### Dependencies (`requirements.txt`)

```
fastapi
uvicorn[standard]
python-multipart
python-dotenv
python-osc
```

`python-osc` is included from the start so the OSC listener can be scaffolded in Phase 3 without changing dependencies.

### Environment Variables (`.env`)

```
PORT=8000
MEDIA_DIR=./media
CUES_FILE=./cues.json
DISPLAY=:0
OSC_PORT=5005
```

`DISPLAY` is used on Linux headless setups (NUC running Ubuntu Server without a desktop environment) to tell mpv which X display or Wayland socket to render to. On Pi OS with a desktop this is typically `:0`. On headless Ubuntu Server see the display setup notes below.

`OSC_PORT` is the UDP port the OSC listener binds to (Phase 3). Default `5005` is the QLab-conventional receive port for a slave device.

### API Endpoints

All responses are JSON.

#### Phase 1 — Web UI endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/cues` | Returns the ordered cue list |
| `POST` | `/api/upload` | Accepts a multipart file upload, appends to cue list |
| `POST` | `/api/cues/reorder` | Accepts a new ordered array of cue IDs, saves to `cues.json` |
| `DELETE` | `/api/cues/{cue_id}` | Removes a cue by UUID, deletes the file |
| `POST` | `/api/cues/{cue_id}/play` | Triggers playback of a cue by UUID |
| `POST` | `/api/stop` | Stops current playback |
| `GET` | `/api/status` | Returns current playback status (`playing`, `stopped`, filename) |

#### Phase 2 — Index-based trigger endpoints

These are the endpoints external tools (QLab, scripts, etc.) use. Cue numbers are 1-based to match convention in show control software.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/go` | Plays the next cue in the list (advances the internal pointer) |
| `POST` | `/api/go/{n}` | Plays cue number `n` (1-based index) |
| `GET` | `/api/current` | Returns which cue is currently active (number + metadata) |
| `POST` | `/api/reset` | Resets the cue pointer back to cue 1 without playing |

**Internal cue pointer:** The backend maintains a current cue index in memory (not persisted). `POST /api/go` plays whatever index comes next and advances the pointer. `POST /api/reset` sets the pointer back to 0 without triggering playback. This mirrors how QLab and similar show control tools think about cue lists.

### Cue List Format (`cues.json`)

```json
[
  {
    "id": "uuid-string",
    "filename": "my-video.mp4",
    "label": "my-video.mp4",
    "type": "video",
    "path": "./media/my-video.mp4"
  }
]
```

- `id`: UUID generated at upload time
- `label`: Editable display name (defaults to filename)
- `type`: `"video"` or `"image"` (derived from file extension at upload)

The schema is intentionally minimal for Phase 1. Future phases will add per-cue fields for playback options (rotation, scale mode, loop, etc.) without breaking existing cue files.

### Player (`player.py`)

- Manages a single `mpv` subprocess
- Before launching a new file, terminate any running mpv process
- Always launches fullscreen — no toggle
- Launch command:
  ```python
  cmd = [
      "mpv",
      "--fullscreen",
      "--no-terminal",       # suppress terminal output
      filepath
  ]
  # For images, hold until explicitly stopped:
  if media_type == "image":
      cmd += ["--image-display-duration=inf"]
  ```
- Pass `DISPLAY` environment variable from `.env` into the subprocess environment on Linux so mpv knows which display to render to:
  ```python
  import os, subprocess
  env = {**os.environ, "DISPLAY": settings.display}
  proc = subprocess.Popen(cmd, env=env)
  ```
- Expose `play(filepath, media_type)`, `stop()`, and `status()` methods
- Track the running process with `subprocess.Popen`, stored as a module-level variable

#### Platform Notes for Display Output

**Raspberry Pi 4 (Pi OS Bookworm):** Uses KMS/DRM by default. mpv works out of the box with `--fullscreen` when a desktop session is running. For headless (no desktop), use `--vo=drm` and set `--drm-connector` if needed.

**Raspberry Pi 5 (Pi OS Bookworm):** KMS only (no legacy FKMS). Same as Pi 4 headless: `--vo=drm` for headless, or desktop session for standard `--fullscreen`.

**Ubuntu Server on NUC (headless):** No display server runs by default. Two options:
1. Install a minimal desktop: `sudo apt install --no-install-recommends xorg openbox` then start with `startx` on boot
2. Use mpv's DRM/KMS output directly: `--vo=drm` — no display server needed, renders directly to framebuffer

For Phase 1, assume a desktop session is running on the target device. Document the headless DRM path as a known alternative but don't build it yet.

The `player.py` abstraction should make it easy to inject extra mpv flags per platform in a later phase.

### Static File Serving (Production)

FastAPI should serve the built React app from `frontend/dist/`:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

Mount this **after** all `/api` routes so API routes take priority.

---

## Frontend

### Dependencies

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "@hello-pangea/dnd": "^16"
  },
  "devDependencies": {
    "vite": "^5",
    "@vitejs/plugin-react": "^4"
  }
}
```

- Use `@hello-pangea/dnd` (maintained fork of `react-beautiful-dnd`) for drag-to-reorder
- No CSS framework needed — keep styles minimal and inline or in a single CSS file

### Vite Proxy Config (`vite.config.js`)

```js
export default {
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

### UI Layout

Single-page app. No routing needed.

```
┌─────────────────────────────────┐
│         🎬 Cutie Pi             │
├─────────────────────────────────┤
│  [ Drop files here / Browse ]   │  ← UploadZone
├─────────────────────────────────┤
│  Cue List                       │
│  ┌───────────────────────────┐  │
│  │ ☰  1. my-video.mp4   ▶  🗑 │  │  ← CueItem (draggable)
│  │ ☰  2. photo.jpg      ▶  🗑 │  │
│  │ ☰  3. outro.mp4      ▶  🗑 │  │
│  └───────────────────────────┘  │
│  [ ⏹ Stop Playback ]            │
└─────────────────────────────────┘
```

### Component Behaviour

**UploadZone**
- Accepts drag-and-drop or click-to-browse
- Filters to allowed extensions (`.jpg .jpeg .png .gif .mp4 .mov .webm`)
- Shows upload progress indicator
- On success, refreshes the cue list

**CueList**
- Fetches `/api/cues` on mount and after any mutation
- Wraps items in `@hello-pangea/dnd` `DragDropContext` and `Droppable`
- On drag end, calls `POST /api/cues/reorder` with the new order

**CueItem**
- Displays cue number (position in list), filename/label
- Play button (▶) calls `POST /api/cues/{id}/play`
- Delete button (🗑) calls `DELETE /api/cues/{id}`, then refreshes list
- Visual indicator if this cue is currently playing (poll `/api/status` every 2 seconds)

**Stop Button**
- Calls `POST /api/stop`

---

## Development Setup & Testing

The goal is to be able to develop and test the full app — including the REST API and OSC trigger paths — without touching a Pi or NUC. There are two viable local environments:

### Option A: Native macOS (fastest, covers ~90%)

The entire app runs on a Mac. mpv opens in a window instead of fullscreen, which is fine for development.

```bash
# Prerequisites
brew install mpv node python@3.11

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # DISPLAY can be left blank on macOS
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

What you can test on Mac: everything. Upload, cue list ordering, playback (windowed), REST API endpoints, OSC receive. The only thing that won't match production is fullscreen and the specific display output behaviour on Pi/NUC hardware.

### Option B: Ubuntu Server VM via UTM (closest to production)

For testing the Linux display stack, systemd autostart, or headless NUC behaviour without real hardware. **UTM** is the recommended VM tool on Apple Silicon Macs (free, native ARM).

**Setup:**
1. Download UTM from [utm.app](https://utm.app) (free)
2. Download Ubuntu Server 24.04 ARM64 ISO
3. Create a new VM in UTM: Linux, 2GB RAM, 20GB disk, attach the ISO
4. Install Ubuntu Server (no desktop needed for API/OSC testing; add `xorg openbox` if you want to test actual video output)
5. In UTM network settings, use **Bridged** mode so the VM gets its own IP on your local network — this lets you test hitting it from your Mac browser just like a real device

**In the VM:**
```bash
sudo apt update && sudo apt install -y mpv python3-pip python3-venv git
git clone <your-repo> cutie-pi
cd cutie-pi/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set DISPLAY=:0 if desktop is running
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then from your Mac browser: `http://<vm-ip>:8000`

**When to use the VM vs native Mac:**

| Scenario | Mac native | Ubuntu VM |
|----------|-----------|-----------|
| UI development | ✅ | ✅ |
| REST API testing | ✅ | ✅ |
| OSC testing | ✅ | ✅ |
| systemd autostart | ❌ | ✅ |
| Linux display/mpv flags | ❌ | ✅ |
| Fullscreen playback | ❌ | ✅ (with desktop) |
| Exact Pi hardware | ❌ | ❌ |

### Testing the REST API (Phase 2)

Once the backend is running, test endpoints directly with `curl` or any REST client (Bruno, Insomnia, Postman, etc.):

```bash
# List cues
curl http://localhost:8000/api/cues

# Trigger cue 1 by index
curl -X POST http://localhost:8000/api/go/1

# Advance to next cue
curl -X POST http://localhost:8000/api/go

# Check current cue
curl http://localhost:8000/api/current

# Stop playback
curl -X POST http://localhost:8000/api/stop

# Reset cue pointer
curl -X POST http://localhost:8000/api/reset
```

FastAPI also auto-generates interactive docs at `http://localhost:8000/docs` — use this to explore and test all endpoints without writing curl commands.

### Testing OSC (Phase 3)

**Send test OSC messages from your Mac** using one of these free tools:

- **TouchOSC** (iOS/macOS) — build a simple button layout that sends `/cue/1`, `/cue/2`, etc.
- **OSC/PILOT** — free browser-based OSC sender, no install
- **Python one-liner** (fastest for dev testing):

```python
# pip install python-osc
from pythonosc.udp_client import SimpleUDPClient
client = SimpleUDPClient("127.0.0.1", 5005)
client.send_message("/cue/1", [])    # trigger cue 1
client.send_message("/go", [])       # advance
client.send_message("/stop", [])     # stop
```

**To test from QLab** (if you have it):
- In QLab, create a Network cue
- Set destination to the Pi/Mac IP, port `5005`
- Message type: OSC
- Address: `/cue/1` (or `/go`, `/stop`)

---

## Phase 2 — REST API

Phase 2 adds index-based trigger endpoints to `main.py`. No new files needed — just new routes and a cue pointer tracked in application state.

### Cue Pointer

Add a module-level state object in `main.py`:

```python
class AppState:
    current_index: int = 0   # 0 = before first cue, i.e. next GO plays cue 1

state = AppState()
```

This is in-memory only — it resets to 0 on server restart. That's intentional; the cue list order is the source of truth, not the pointer position.

### New Routes

```python
@app.post("/api/go")
def go_next():
    """Advance to and play the next cue."""

@app.post("/api/go/{n}")
def go_to(n: int):
    """Play cue number n (1-based)."""

@app.get("/api/current")
def current_cue():
    """Return the currently active cue number and metadata."""

@app.post("/api/reset")
def reset():
    """Reset cue pointer to 0 (before cue 1) without playing."""
```

### UI Changes for Phase 2

- Highlight the currently pointed-to cue in the cue list (distinct from the currently *playing* cue — these can differ if cue pointer was advanced manually)
- Add a **GO** button prominently at the top/bottom of the cue list as a big, tap-friendly button — this is the main performance control
- Add a **Reset** button next to GO

```
┌─────────────────────────────────┐
│         🎬 Cutie Pi             │
├─────────────────────────────────┤
│  [ Drop files here / Browse ]   │
├─────────────────────────────────┤
│  [ ▶▶ GO ]          [ ↺ Reset ] │  ← New in Phase 2
├─────────────────────────────────┤
│  Cue List                       │
│  ┌───────────────────────────┐  │
│  │ ► 1. my-video.mp4    ▶  🗑│  │  ← ► = pointer position
│  │   2. photo.jpg       ▶  🗑│  │
│  │   3. outro.mp4       ▶  🗑│  │
│  └───────────────────────────┘  │
│  [ ⏹ Stop ]                     │
└─────────────────────────────────┘
```

---

## Phase 3 — OSC

Phase 3 adds a UDP OSC listener that runs in a background thread alongside FastAPI. It maps incoming OSC messages to the same internal logic as the REST API — no duplication of playback logic.

### New File: `osc_server.py`

```python
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
import threading

def start_osc_server(host, port, play_fn, go_fn, stop_fn, reset_fn):
    dispatcher = Dispatcher()
    dispatcher.map("/cue/*", handle_cue, play_fn)   # /cue/1, /cue/2, etc.
    dispatcher.map("/go", lambda *a: go_fn())
    dispatcher.map("/stop", lambda *a: stop_fn())
    dispatcher.map("/reset", lambda *a: reset_fn())

    server = BlockingOSCUDPServer((host, port), dispatcher)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
```

Start the OSC server in `main.py` on FastAPI startup:

```python
@app.on_event("startup")
def startup():
    start_osc_server(
        "0.0.0.0",
        settings.osc_port,
        play_fn=player.play_by_index,
        go_fn=player.go_next,
        stop_fn=player.stop,
        reset_fn=state.reset
    )
```

### OSC Address Map

| OSC Address | Argument | Action |
|-------------|----------|--------|
| `/go` | none | Play next cue (same as `POST /api/go`) |
| `/cue/1` | none | Play cue 1 (same as `POST /api/go/1`) |
| `/cue/n` | none | Play cue n |
| `/stop` | none | Stop playback |
| `/reset` | none | Reset cue pointer |

Cue numbers are 1-based to match QLab convention.

### QLab Integration Notes

QLab is the most common show control tool this will be used with. To trigger Cutie Pi from QLab:

1. In QLab, go to **Settings → Network**
2. Add a destination: IP = Cutie Pi's IP, Port = `5005`, type = OSC
3. Create a **Network cue** in your cue list
4. Set message to OSC, address `/go` or `/cue/1` etc.
5. No arguments needed

QLab can also receive OSC back from Cutie Pi if feedback is needed (e.g. playback-complete notification) — this is out of scope but the architecture supports it.

---

## Autostart on Linux (systemd) — implement last

Works the same on Pi OS and Ubuntu Server. Create `/etc/systemd/system/cutie-pi.service`:

```ini
[Unit]
Description=Cutie Pi Media Server
After=network.target graphical.target

[Service]
WorkingDirectory=/home/pi/cutie-pi/backend
ExecStart=/home/pi/cutie-pi/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
User=pi
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
```

Adjust `User` and `WorkingDirectory` for the NUC (likely `ubuntu` instead of `pi`).

```bash
sudo systemctl enable cutie-pi
sudo systemctl start cutie-pi
```

---

## Future / Out of Scope

- Per-cue playback options: scale mode, rotation, stretch/fit/fill, position (store in `cues.json`, pass as mpv flags)
- Cue label editing in the UI
- Looping / auto-advance between cues
- Headless DRM/KMS playback mode (`--vo=drm`) for NUCs or Pis without a desktop session
- macOS and Windows support
- OSC feedback from Cutie Pi back to QLab (e.g. playback-complete, cue-loaded)
- Authentication / access control