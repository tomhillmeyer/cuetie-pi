import os
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

import player
import cues

load_dotenv()

media_dir = os.getenv("MEDIA_DIR", "./media")
cues_file = os.getenv("CUES_FILE", "./cues.json")
display = os.getenv("DISPLAY", ":0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(media_dir).mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/cues")
def get_cues():
    return cues.load_cues(cues_file)

@app.post("/api/upload")
async def upload_media(file: UploadFile = File(...)):
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_name = Path(filename).name
    save_path = Path(media_dir) / safe_name
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Determine if video (needs transcode)
    media_type = cues.guess_media_type(safe_name)
    
    if media_type == "video":
        # Start transcode in background
        temp_output = Path(media_dir) / f".{safe_name}.transcoded.mp4"
        output_path = str(temp_output)
        
        # Add cue with "processing" status
        cue = cues.add_cue(cues_file, safe_name, media_dir, "processing")
        
        # Trigger background transcode (pass original path for cleanup later)
        player.transcode_video(
            str(save_path),  # original input
            output_path,    # temp output
            str(save_path), # original to delete after success
            cue["id"],
            cues_file
        )
    else:
        cue = cues.add_cue(cues_file, safe_name, media_dir, "ready")
    
    return cue

@app.post("/api/cues/reorder")
def reorder_cues(body: dict):
    cue_ids = body.get("cueIds", [])
    reordered = cues.reorder_cues(cues_file, cue_ids)
    return reordered

@app.delete("/api/cues/{cue_id}")
def delete_cue(cue_id: str):
    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")

    file_path = Path(cue["path"])
    if file_path.exists():
        file_path.unlink()

    cues.remove_cue(cues_file, cue_id)
    return {"success": True}

@app.post("/api/cues/{cue_id}/play")
def play_cue(cue_id: str):
    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")

    file_path = Path(cue["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    player.play(cue_id, str(file_path), cue.get("type"), display)
    return {"success": True, "cue": cue}

@app.post("/api/stop")
def stop_playback():
    player.stop()
    return {"success": True}

@app.get("/api/status")
def get_status():
    return player.status()

@app.get("/api/stats")
def get_stats():
    return player.get_stats()

@app.get("/api/debug")
def get_debug():
    return player.debug()

@app.get("/api/debug-logs")
def get_debug_logs():
    import os
    log_file = "/tmp/mpv.log"
    if not os.path.exists(log_file):
        return {"exists": False, "content": ""}
    with open(log_file, "r") as f:
        content = f.read()
    return {"exists": True, "content": content[-20000:]}

app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")