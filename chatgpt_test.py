import threading
import subprocess
import time

class DevicePinger:
    def __init__(self, device_ip):
        self.device_ip = device_ip
        self.device_availability = {}
        self.interval_seconds = 3600  # Ping every hour
        self.thread = None

    def ping_device(self):
        while True:
            try:
                subprocess.check_output(["ping", "-c", "3", self.device_ip])
                availability = True  # Device is online
            except subprocess.CalledProcessError:
                availability = False  # Device is offline

            timestamp = int(time.time())
            self.device_availability[timestamp] = availability

            time.sleep(self.interval_seconds)

    def start_pinging(self):
        self.thread = threading.Thread(target=self.ping_device)
        self.thread.start()

# Usage example
if __name__ == "__main__":
    device_pinger = DevicePinger(device_ip="192.168.68.50")

    # Start pinging in a thread
    device_pinger.start_pinging()

    # Main program (for demonstration purposes)
    try:
        while True:
            # Do other things while the device pinger is running
            print("Main program running...")
            time.sleep(2)

            # Access the device availability dictionary
            current_availability = device_pinger.device_availability
            print(f"Device availability: {current_availability}")

    except KeyboardInterrupt:
        print("Received Ctrl+C. Stopping the device pinger and terminating the program.")
        # If needed, you can stop the device pinger thread gracefully
        if device_pinger.thread:
            device_pinger.thread.join()

        # Perform cleanup or additional actions as needed
