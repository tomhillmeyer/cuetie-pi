# Cutie Pi API Reference

All endpoints are at `http://<host>:8000`. All responses are JSON.

---

## Cues

### GET /api/cues

Return the full ordered cue list.

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "my-video.mp4",
    "label": "my-video.mp4",
    "type": "video",
    "path": "./media/my-video.mp4",
    "status": "ready"
  }
]
```

### POST /api/upload

Upload a media file and create a cue. Accepts multipart/form-data.

**Body**: `file` (multipart file)

**Response**: The new cue object (see schema above).

**Supported types**: `.jpg`, `.jpeg`, `.png`, `.gif` (image), `.mp4`, `.mov`, `.webm` (video)

### POST /api/cues/reorder

Reorder cues by providing the full ordered list of cue IDs.

**Body**:
```json
{
  "cueIds": ["id3", "id1", "id2"]
}
```

**Response**: The reordered cue array.

### DELETE /api/cues/{cue_id}

Delete a cue and its media file.

**Response**: `{"success": true}`

---

## Playback

### POST /api/cues/{cue_id}/play

Play a cue by UUID. Also sets the cue pointer to this cue's position.

**Response**:
```json
{
  "success": true,
  "cue": { "id": "...", "filename": "...", "type": "video", ... }
}
```

### POST /api/stop

Stop playback. Shows a black screen (`black.png`). The cue pointer is not changed.

**Response**: `{"success": true}`

### GET /api/status

Return current playback status (from mpv).

**Response** (idle):
```json
{
  "status": "idle",
  "filename": null,
  "cueId": null
}
```

**Response** (playing):
```json
{
  "status": "playing",
  "filename": "./media/my-video.mp4",
  "cueId": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Index-based Triggering

These endpoints use an internal cue pointer (1-based, in-memory, resets on restart).

### POST /api/go

Advance the pointer to the next cue and play it. Wraps to cue 1 if already at the last cue.

**Response**:
```json
{
  "success": true,
  "cue": { "id": "...", ... },
  "index": 2
}
```

**Error** (no cues):
```json
{
  "success": false,
  "error": "No cues in list"
}
```

### POST /api/go/{n}

Play cue number `n` (1-based). Sets the pointer to `n`.

**Response**: Same as `/api/go`.

**Error** (invalid n):
```json
{
  "success": false,
  "error": "Invalid cue number: 0"
}
```

### POST /api/previous

Play the previous cue. Stays at cue 1 if already at 1.

**Response**: Same format as `/api/go`.

### GET /api/current

Return the currently pointed-to cue (not necessarily the playing cue).

**Response** (no cues or pointer at 0):
```json
{
  "index": 0,
  "cue": null
}
```

**Response** (pointing to cue 2):
```json
{
  "index": 2,
  "cue": { "id": "...", ... }
}
```

### POST /api/reset

Reset the cue pointer to 0 (before cue 1). Does not trigger playback.

**Response**: `{"success": true, "index": 0}`

---

## Stats & Debug

### GET /api/stats

Return detailed playback statistics from mpv.

**Response** (idle):
```json
{
  "status": "idle",
  "playback-time": null,
  "duration": null,
  "percent-pos": null,
  "fps": null,
  "video-params": {},
  "filename": null,
  "video-codec": null,
  "dropped-frames": null,
  ...
}
```

**Response** (playing):
```json
{
  "status": "playing",
  "paused": false,
  "playback-time": 10.5,
  "duration": 120.0,
  "percent-pos": 8.75,
  "fps": 29.97,
  "vsync": 29.97,
  "hwdec": "drm-copy",
  "decoder": "h264",
  "video-params": { "w": "1920", "h": "1080" },
  "filename": "./media/my-video.mp4",
  "media-title": "my-video.mp4",
  "video-codec": "h264",
  "dropped-frames": 0
}
```

### GET /api/debug

Return mpv startup logs, process status, and property query results for troubleshooting.

**Response**:
```json
{
  "proc_running": true,
  "proc_poll": null,
  "current_file": "./media/my-video.mp4",
  "current_cue_id": "550e...",
  "socket_exists": true,
  "socket_path": "/tmp/mpv-socket",
  "test_properties": { "time-pos": 10.5, ... },
  "startup_logs": ""
}
```

---

## WebSocket

### ws://\<host\>:8000/ws/status

A single WebSocket connection delivers both status updates and playback statistics as typed JSON messages. No authentication required.

**On connect**: Server immediately sends the current status. If a cue is playing, it also sends one stats snapshot.

**While idle**: Only status messages are sent (on state transitions like upload, reorder, stop).

**While playing**: A status message is sent on every state change (play, stop, go). Statistics are pushed every **500ms** via a shared server-side timer.

### Message Types

#### Status messages (`type: "status"`)

Sent on connect, play, stop, go, and any state transition.

```json
{
  "type": "status",
  "status": "playing",
  "filename": "./media/my-video.mp4",
  "cueId": "550e8400-e29b-41d4-a716-446655440000"
}
```

```json
{
  "type": "status",
  "status": "idle",
  "filename": null,
  "cueId": null
}
```

#### Stats messages (`type: "stats"`)

Pushed every 500ms while a cue is playing. Identical payload to `GET /api/stats` with an added `type` field.

```json
{
  "type": "stats",
  "status": "playing",
  "paused": false,
  "playback-time": 10.5,
  "duration": 120.0,
  "percent-pos": 8.75,
  "fps": 29.97,
  "vsync": 29.97,
  "hwdec": "drm-copy",
  "decoder": "h264",
  "video-params": { "w": "1920", "h": "1080" },
  "filename": "./media/my-video.mp4",
  "video-codec": "h264",
  "dropped-frames": 0
}
```

When playback stops, the stats loop is cancelled — no final stats message is pushed. Clients should use the `status` message type to detect idle transitions.

---

## Cue Schema

Stored in `cues.json`:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "my-video.mp4",
    "label": "my-video.mp4",
    "type": "video",
    "path": "./media/my-video.mp4",
    "status": "ready"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID generated at upload |
| `filename` | string | Original filename |
| `label` | string | Display name (defaults to filename) |
| `type` | string | `"video"` or `"image"` (derived from extension) |
| `path` | string | Filesystem path relative to backend |
| `status` | string | Cue status (`"ready"`, `"processing"`, `"error"`) |

---

## Cue Pointer

The backend maintains a single integer pointer (`current_index`) in memory:

- `0` = before the first cue (e.g. after reset or initial load)
- `1` = first cue in the list
- Updated by: `/api/go`, `/api/go/{n}`, `/api/previous`, `/api/reset`, `/api/cues/{id}/play`
- **Not persisted** — resets to 0 on server restart

---

## Example Workflows

### Basic: Upload, list, and play

```bash
# Upload a file
curl -X POST -F "file=@my-video.mp4" http://host:8000/api/upload

# List cues
curl http://host:8000/api/cues

# Play the first cue
curl -X POST http://host:8000/api/go/1

# Play next cue
curl -X POST http://host:8000/api/go

# Stop
curl -X POST http://host:8000/api/stop

# Check status
curl http://host:8000/api/status
```

### Show control (QLab, scripts)

```bash
# Reset pointer at show start
curl -X POST http://host:8000/api/reset

# On each cue press:
curl -X POST http://host:8000/api/go

# Jump to a specific cue (e.g. during rehearsal)
curl -X POST http://host:8000/api/go/3

# Emergency stop
curl -X POST http://host:8000/api/stop
```
