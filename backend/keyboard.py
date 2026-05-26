import threading
import time
import requests
from evdev import InputDevice, ecodes, list_devices

API_URL = "http://localhost:8000"

KEYBOARD_DEBOUNCE = 0.2  # seconds
_key_last_pressed = {"right": 0, "left": 0}

_watched_devices: set[str] = set()
_watch_lock = threading.Lock()


def on_key_event(key_direction):
    now = time.time()
    last_time = _key_last_pressed.get(key_direction, 0)
    if now - last_time < KEYBOARD_DEBOUNCE:
        return
    _key_last_pressed[key_direction] = now
    try:
        if key_direction == "right":
            requests.post(f"{API_URL}/api/go", timeout=1)
        elif key_direction == "left":
            requests.post(f"{API_URL}/api/previous", timeout=1)
    except Exception:
        pass


def device_listener(device):
    try:
        for event in device.async_read_loop():
            if event.type == ecodes.EV_KEY:
                if event.value == 1:
                    if event.code == ecodes.KEY_RIGHT:
                        on_key_event("right")
                    elif event.code == ecodes.KEY_LEFT:
                        on_key_event("left")
    except Exception:
        pass


def _listen_device(path: str):
    try:
        device = InputDevice(path)
        with _watch_lock:
            _watched_devices.add(path)
        thread = threading.Thread(
            target=device_listener,
            args=(device,),
            daemon=True,
        )
        thread.start()
        return True
    except Exception:
        return False


def _scan_and_listen():
    paths = list_devices()
    with _watch_lock:
        new_paths = [p for p in paths if p not in _watched_devices]
    count = 0
    for path in new_paths:
        if _listen_device(path):
            count += 1
    if count:
        print(f"[keyboard] Watching {count} new device(s)", flush=True)


def _watch_loop():
    while True:
        time.sleep(2)
        try:
            _scan_and_listen()
        except Exception:
            pass


def start_keyboard_listener():
    _scan_and_listen()
    thread = threading.Thread(target=_watch_loop, daemon=True)
    thread.start()
    print("[keyboard] Listener active (polling for hotplug)", flush=True)