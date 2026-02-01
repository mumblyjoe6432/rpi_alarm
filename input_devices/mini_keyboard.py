from queue import Queue
import threading
import logging
from evdev import InputDevice, categorize, ecodes, list_devices
import pdb

class mini_keyboard:
    """
    The mini-keybaord controller class controlls the mini keyboard. Presumably it works with many types, but
    the type it was tested for is:
    https://www.amazon.com/dp/B09Z613J78?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1

    Mini USB keyboard(s) with 12 buttons + 2 rotary dials.
    Orientation: dials at the bottom, 4 rows x 3 columns of keys above.

    Layout mapping (R = row, C = column):
        R1C1 R1C2 R1C3
        R2C1 R2C2 R2C3
        R3C1 R3C2 R3C3
        R4C1 R4C2 R4C3
    Dials:
        dial_left_up, dial_left_down, dial_left_press
        dial_right_up, dial_right_down, dial_right_press

    Usage:
        kb = mini_keyboard("USB Composite Device Keyboard")
        if not kb.keypad_queue.empty():
            btn = kb.keypad_queue.get()
            # process btn (e.g. "R2C3" or "dial_left_up")
    """

    def __init__(self, device_name_filter="USB Composite Device Keyboard"):
        self.keypad_queue = Queue()
        self.stop_flag = threading.Event()
        self.threads = []
        self.devices = []

        # Find all matching input devices
        for path in list_devices():
            dev = InputDevice(path)
            if device_name_filter in dev.name:
                self.devices.append(dev)

        if not self.devices:
            raise RuntimeError("No mini keyboard devices found")

        logging.info(f"Mini keyboard(s) found: {[d.path for d in self.devices]}")

        # Start one reader thread per device
        for dev in self.devices:
            t = threading.Thread(target=self._event_loop, args=(dev,), daemon=True)
            t.start()
            self.threads.append(t)

    def _event_loop(self, device):
        for event in device.read_loop():
            if self.stop_flag.is_set():
                break
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down:
                    btn = self._map_key(event.code)
                    if btn:
                        logging.debug(f"Mini keyboard event: {btn}")
                        self.keypad_queue.put(btn)

    def _map_key(self, code):
        """
        Convert evdev key codes into normalized button/dial labels.
        """
        mapping = {
            # 12 buttons
            ecodes.KEY_I: "R1C1",
            ecodes.KEY_E: "R1C2",
            ecodes.KEY_A: "R1C3",
            ecodes.KEY_J: "R2C1",
            ecodes.KEY_F: "R2C2",
            ecodes.KEY_B: "R2C3",
            ecodes.KEY_K: "R3C1",
            ecodes.KEY_G: "R3C2",
            ecodes.KEY_C: "R3C3",
            ecodes.KEY_L: "R4C1",
            ecodes.KEY_H: "R4C2",
            ecodes.KEY_D: "R4C3",

            # Right dial
            ecodes.KEY_3: "dial_right_up",
            ecodes.KEY_1: "dial_right_down",
            ecodes.KEY_2: "dial_right_press",

            # Left dial
            ecodes.KEY_6: "dial_left_up",
            ecodes.KEY_4: "dial_left_down",
            ecodes.KEY_5: "dial_left_press",
        }
        return mapping.get(code)

    def stop_thread(self):
        """
        Stop all background threads cleanly.
        """
        self.stop_flag.set()
        for t in self.threads:
            t.join()
