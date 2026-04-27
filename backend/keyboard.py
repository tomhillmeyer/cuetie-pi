import threading
import time
import requests
from evdev import InputDevice, ecodes, list_devices

API_URL = "http://localhost:8000"

KEYBOARD_DEBOUNCE = 0.2  # seconds
_key_last_pressed = {"right": 0, "left": 0}

def start_keyboard_listener():
    """Listen for arrow key presses on ALL input devices."""
    
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
    
    def device_listener(device):
        """Listen to a single device for key events."""
        try:
            for event in device.async_read_loop():
                if event.type == ecodes.EV_KEY:
                    if event.value == 1:  # key down only
                        if event.code == ecodes.KEY_RIGHT:
                            on_key_event("right")
                        elif event.code == ecodes.KEY_LEFT:
                            on_key_event("left")
        except Exception as e:
            pass
    
    def start_all_devices():
        """Start listening to all input devices."""
        try:
            devices = [InputDevice(path) for path in list_devices()]
            
            if not devices:
                print("No input devices found - keyboard control disabled")
                return
            
            print(f"Keyboard listener started on {len(devices)} device(s)")
            
            for device in devices:
                thread = threading.Thread(
                    target=device_listener, 
                    args=(device,), 
                    daemon=True
                )
                thread.start()
        except Exception as e:
            print(f"Keyboard listener error: {e}")
    
    start_all_devices()