import threading
import time
import requests
from evdev import InputDevice, ecodes, list_devices

API_URL = "http://localhost:8000"

KEYBOARD_DEBOUNCE = 0.2  # seconds
_key_last_pressed = {"right": 0, "left": 0}

def start_keyboard_listener():
    """Find keyboard device and listen for arrow key presses."""
    def find_keyboard():
        """Find the first keyboard device."""
        try:
            devices = [InputDevice(path) for path in list_devices()]
            for device in devices:
                if 'keyboard' in device.name.lower() or 'kbd' in device.name.lower():
                    return device
            return None
        except Exception:
            return None

    def on_key_event(key_direction):
        """Handle a key press - call the appropriate API."""
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

    def listen_loop():
        keyboard = find_keyboard()
        if keyboard is None:
            print("No keyboard device found - keyboard control disabled")
            return
        
        print(f"Keyboard listener started: {keyboard.name}")
        
        try:
            for event in keyboard.async_read_loop():
                if event.type == ecodes.EV_KEY:
                    if event.value == 1:
                        if event.code == ecodes.KEY_RIGHT:
                            on_key_event("right")
                        elif event.code == ecodes.KEY_LEFT:
                            on_key_event("left")
        except Exception as e:
            print(f"Keyboard listener error: {e}")

    thread = threading.Thread(target=listen_loop, daemon=True)
    thread.start()
    return thread