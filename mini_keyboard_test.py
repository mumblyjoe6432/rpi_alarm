import time
from evdev import InputDevice, categorize, ecodes, list_devices

# Find your keypad device
print("Available input devices:")
devices = [InputDevice(path) for path in list_devices()]
for i, dev in enumerate(devices):
    print(f"{i}: {dev.name} ({dev.path})")

choice = int(input("Select your device number: "))
device = devices[choice]
print(f"\nListening to: {device.name} ({device.path})")
print("Press buttons or turn dials...\n")

for event in device.read_loop():
    if event.type == ecodes.EV_KEY:
        key_event = categorize(event)
        if key_event.keystate == key_event.key_down:
            print(f"[BUTTON] {key_event.keycode} pressed")

    elif event.type == ecodes.EV_REL:
        if event.code == ecodes.REL_DIAL:
            direction = "clockwise" if event.value > 0 else "counter-clockwise"
            print(f"[DIAL] Dial rotated {direction}")
        elif event.code == ecodes.REL_WHEEL:
            direction = "up" if event.value > 0 else "down"
            print(f"[WHEEL] Wheel moved {direction}")
        elif event.code in (ecodes.REL_X, ecodes.REL_Y):
            axis = "X" if event.code == ecodes.REL_X else "Y"
            print(f"[MOTION] {axis}-axis movement: {event.value}")
