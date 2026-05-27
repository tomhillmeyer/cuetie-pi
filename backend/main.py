import os
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

import aiofiles

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from dotenv import load_dotenv

import player
import cues
import keyboard
import generate_splash
import usb_import
import usb_config

load_dotenv()

media_dir = os.getenv("MEDIA_DIR", "./media")
cues_file = os.getenv("CUES_FILE", "./cues.json")
display = os.getenv("DISPLAY", ":0")


class AppState:
    def __init__(self):
        self.current_index: int = 0
        self.num_cues: int = 0


state = AppState()
connected_clients: set[WebSocket] = set()
_stats_task: asyncio.Task | None = None
_splash_network_task: asyncio.Task | None = None
_usb_import_task: asyncio.Task | None = None


def update_num_cues():
    all_cues = cues.load_cues(cues_file)
    state.num_cues = len(all_cues)


async def _push_stats_loop():
    try:
        while True:
            await asyncio.sleep(0.5)
            stats = player.get_stats()
            msg = {"type": "stats", **stats}
            dead = set()
            for ws in connected_clients:
                try:
                    await ws.send_json(msg)
                except Exception:
                    dead.add(ws)
            connected_clients.difference_update(dead)
    except asyncio.CancelledError:
        pass


def _refresh_cues_display():
    generate_splash.generate(str(splash_logo), str(splash_path))
    player.refresh_splash()


async def broadcast_cues_updated():
    dead = set()
    msg = {"type": "cues_updated"}
    for ws in connected_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)


async def broadcast_status():
    global _stats_task
    status = player.status()
    msg = {"type": "status", **status}
    dead = set()
    for ws in connected_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)

    if status["status"] == "playing":
        if _stats_task is None or _stats_task.done():
            _stats_task = asyncio.create_task(_push_stats_loop())
    else:
        if _stats_task is not None and not _stats_task.done():
            _stats_task.cancel()
            _stats_task = None


splash_logo = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "logo.png"
splash_path = Path(generate_splash.__file__).parent / "splash.png"


async def _splash_network_watcher():
    last_ip = None
    while True:
        await asyncio.sleep(10)
        try:
            ips = generate_splash.get_primary_ip()
            if not ips:
                continue
            current = ips[0]
            if current != last_ip:
                last_ip = current
                _refresh_cues_display()
                print(f"[splash] Updated for IP: {current}", flush=True)
        except Exception:
            pass


async def _usb_import_loop():
    while True:
        await asyncio.sleep(5)
        try:
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            count = usb_import.import_usb(media_dir, cues_file, env_path=env_path)
            if count:
                await broadcast_cues_updated()
                _refresh_cues_display()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _splash_network_task, _usb_import_task
    Path(media_dir).mkdir(parents=True, exist_ok=True)
    update_num_cues()
    try:
        keyboard.start_keyboard_listener()
    except Exception as e:
        print(f"Keyboard listener failed to start: {e}")

    try:
        player.show_splash(display)
    except Exception as e:
        print(f"[splash] Failed to show splash screen: {e}")

    _splash_network_task = asyncio.create_task(_splash_network_watcher())
    _usb_import_task = asyncio.create_task(_usb_import_loop())

    yield
    if _stats_task is not None and not _stats_task.done():
        _stats_task.cancel()
    if _splash_network_task is not None and not _splash_network_task.done():
        _splash_network_task.cancel()
    if _usb_import_task is not None and not _usb_import_task.done():
        _usb_import_task.cancel()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def add_cross_origin_isolation(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response


@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        status = player.status()
        await websocket.send_json({"type": "status", **status})
        if status["status"] == "playing":
            await websocket.send_json({"type": "stats", **player.get_stats()})
        while True:
            text = await websocket.receive_text()
            if text == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        connected_clients.discard(websocket)


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
    content = await file.read()
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    player.resize_image(str(save_path))

    media_type = cues.guess_media_type(safe_name)
    cue = cues.add_cue(cues_file, safe_name, media_dir, "ready")

    _refresh_cues_display()
    await broadcast_cues_updated()
    return cue


@app.post("/api/cues/reorder")
async def reorder_cues(body: dict):
    cue_ids = body.get("cueIds", [])
    reordered = cues.reorder_cues(cues_file, cue_ids)

    if state.current_index > 0:
        playing_cue_id = player.get_current_playing_cue_id()
        if playing_cue_id:
            new_index = next((i for i, c in enumerate(reordered) if c["id"] == playing_cue_id), None)
            if new_index is not None:
                state.current_index = new_index + 1

    state.num_cues = len(reordered)
    _refresh_cues_display()
    await broadcast_cues_updated()
    return reordered


@app.delete("/api/cues/{cue_id}")
async def delete_cue(cue_id: str):
    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")

    file_path = Path(cue["path"])
    if file_path.exists():
        file_path.unlink()

    cues.remove_cue(cues_file, cue_id)
    _refresh_cues_display()
    await broadcast_cues_updated()
    return {"success": True}


@app.post("/api/cues/{cue_id}/play")
async def play_cue(cue_id: str):
    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(status_code=404, detail="Cue not found")

    file_path = Path(cue["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    cue_index = next((i for i, c in enumerate(all_cues) if c["id"] == cue_id), None)
    if cue_index is not None:
        state.current_index = cue_index + 1
        state.num_cues = len(all_cues)

    player.play(cue["id"], cue["path"], cue.get("type"), display, cue.get("loop", False))
    await broadcast_status()
    return {"success": True, "cue": cue}


@app.post("/api/cues/{cue_id}/loop")
async def toggle_loop(cue_id: str):
    success = cues.update_cue_loop(cues_file, cue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cue not found")

    if player.get_current_playing_cue_id() == cue_id:
        all_cues = cues.load_cues(cues_file)
        cue = next((c for c in all_cues if c["id"] == cue_id), None)
        if cue and cue.get("type") == "video":
            player.set_loop(cue.get("loop", False))

    all_cues = cues.load_cues(cues_file)
    cue = next((c for c in all_cues if c["id"] == cue_id), None)
    return {"success": True, "loop": cue.get("loop", False) if cue else False}


@app.post("/api/stop")
async def stop_playback():
    player.stop()
    await broadcast_status()
    return {"success": True}


@app.get("/api/status")
def get_status():
    return player.status()


@app.get("/api/stats")
def get_stats():
    return player.get_stats()


@app.get("/api/info")
def get_info():
    ips = generate_splash.get_primary_ip()
    port = os.getenv("PORT", "8000")
    return {
        "ip": ips[0] if ips else "127.0.0.1",
        "port": int(port),
    }


@app.get("/api/config-import-status")
def get_config_import_status():
    return usb_config.get_last_import_result()


@app.get("/api/debug")
def get_debug():
    return player.debug()


@app.post("/api/go")
async def go_next():
    update_num_cues()
    if state.num_cues == 0:
        return {"success": False, "error": "No cues in list"}

    all_cues = cues.load_cues(cues_file)

    if state.current_index >= state.num_cues:
        state.current_index = 1
    else:
        state.current_index += 1

    cue = all_cues[state.current_index - 1]
    player.play(cue["id"], cue["path"], cue.get("type"), display, cue.get("loop", False))
    await broadcast_status()
    return {"success": True, "cue": cue, "index": state.current_index}


@app.post("/api/go/{n}")
async def go_to(n: int):
    update_num_cues()
    if state.num_cues == 0:
        return {"success": False, "error": "No cues in list"}

    if n < 1 or n > state.num_cues:
        return {"success": False, "error": f"Invalid cue number: {n}"}

    state.current_index = n
    all_cues = cues.load_cues(cues_file)
    cue = all_cues[n - 1]

    player.play(cue["id"], cue["path"], cue.get("type"), display, cue.get("loop", False))
    await broadcast_status()
    return {"success": True, "cue": cue, "index": n}


@app.post("/api/previous")
async def go_previous():
    update_num_cues()
    if state.num_cues == 0:
        return {"success": False, "error": "No cues in list"}

    all_cues = cues.load_cues(cues_file)

    if state.current_index <= 1:
        state.current_index = state.num_cues
    else:
        state.current_index -= 1

    cue = all_cues[state.current_index - 1]
    player.play(cue["id"], cue["path"], cue.get("type"), display, cue.get("loop", False))
    await broadcast_status()
    return {"success": True, "cue": cue, "index": state.current_index}


@app.get("/api/current")
def get_current():
    update_num_cues()
    if state.num_cues == 0:
        return {"index": 0, "cue": None}

    if state.current_index == 0:
        return {"index": 0, "cue": None}

    all_cues = cues.load_cues(cues_file)
    cue = all_cues[state.current_index - 1] if state.current_index <= len(all_cues) else None
    return {"index": state.current_index, "cue": cue}


@app.post("/api/reset")
def reset_pointer():
    state.current_index = 0
    return {"success": True, "index": 0}


app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
