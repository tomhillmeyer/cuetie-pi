import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import cues
import player

VIDEO_EXTS = {".mp4", ".mov", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif"}
ALLOWED_EXTS = VIDEO_EXTS | IMAGE_EXTS

IMPORTED_DEVICES_FILE = os.path.join(os.path.dirname(__file__), "imported_devices.json")

_imported_uuids: set[str] = set()
_lock = threading.Lock()
_loaded = False


def _load_imported_uuids():
    global _loaded
    if _loaded:
        return
    try:
        with open(IMPORTED_DEVICES_FILE) as f:
            _imported_uuids.update(json.load(f))
    except Exception:
        pass
    _loaded = True


def _save_imported_uuids():
    try:
        with open(IMPORTED_DEVICES_FILE, "w") as f:
            json.dump(sorted(_imported_uuids), f)
    except Exception:
        pass


BLKID = "/usr/sbin/blkid"


def _get_device_uuid(dev_name: str) -> str | None:
    try:
        result = subprocess.run(
            [BLKID, "-s", "UUID", "-o", "value", f"/dev/{dev_name}"],
            capture_output=True, text=True, timeout=5,
        )
        uuid = result.stdout.strip()
        return uuid if uuid else None
    except Exception:
        return None


def _usb_partitions() -> list[dict]:
    try:
        result = subprocess.run(
            ["lsblk", "-o", "NAME,TRAN,MOUNTPOINT,FSTYPE", "-J"],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(result.stdout)
    except Exception:
        return []

    parts = []
    for dev in data.get("blockdevices", []):
        if dev.get("tran") != "usb":
            continue
        for child in dev.get("children", []):
            if child.get("fstype"):
                parts.append(child)
    return parts


def _mount(dev_name: str) -> str | None:
    try:
        result = subprocess.run(
            ["pmount", f"/dev/{dev_name}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.split("\n"):
            if " to /media/" in line:
                return line.split(" to ")[-1].strip()
        return None
    except Exception:
        return None


def _unmount(dev_name: str):
    try:
        subprocess.run(
            ["pumount", f"/dev/{dev_name}"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _ensure_mountpoint(info: dict) -> str | None:
    dev_name = info.get("name", "")
    mountpoint = info.get("mountpoint")
    if mountpoint:
        return mountpoint
    mp = _mount(dev_name)
    if mp:
        info["mountpoint"] = mp
    return mp


def _scan_files(mount_point: str) -> list[Path]:
    root = Path(mount_point)
    if not root.exists():
        return []
    files = []
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTS:
            if f.name.startswith("._"):
                continue
            files.append(f)
    files.sort(key=lambda p: p.name.lower())
    return files


def _import_files(files: list[Path], media_dir: str, cues_file: str) -> int:
    existing = cues.load_cues(cues_file)
    existing_names = {c["filename"] for c in existing}

    count = 0
    for src in files:
        name = src.name
        if name in existing_names:
            continue

        dst = Path(media_dir) / name
        counter = 1
        while dst.exists():
            stem = src.stem
            suffix = src.suffix
            dst = Path(media_dir) / f"{stem}_{counter}{suffix}"
            counter += 1
        try:
            shutil.copy2(str(src), str(dst))
        except Exception:
            continue
        player.resize_image(str(dst))
        media_type = "video" if src.suffix.lower() in VIDEO_EXTS else "image"
        try:
            cues.add_cue(cues_file, dst.name, media_dir, "ready")
            count += 1
        except Exception:
            continue
    return count


def import_usb(media_dir: str, cues_file: str) -> int:
    _load_imported_uuids()
    parts = _usb_partitions()
    total = 0

    for info in parts:
        dev_name = info.get("name", "")

        uuid = _get_device_uuid(dev_name)
        with _lock:
            if uuid and uuid in _imported_uuids:
                continue

        was_mounted = bool(info.get("mountpoint"))
        mount_point = _ensure_mountpoint(info)
        if not mount_point:
            continue

        try:
            files = _scan_files(mount_point)
            if not files:
                continue

            count = _import_files(files, media_dir, cues_file)
            if count:
                print(
                    f"[usb] Imported {count} file(s) from {dev_name}",
                    flush=True,
                )
                total += count
        finally:
            if not was_mounted:
                _unmount(dev_name)
            if uuid:
                with _lock:
                    _imported_uuids.add(uuid)
                    _save_imported_uuids()

    return total
