import logging
import time, os
import threading

class device_tracker:
    """
    Description:
    This class tracks a device by its IP address. It pings the device every hour
    and records whether it recieves a reply. Then the parent can call
    is_device_present(num_hours), which will return true if the device was
    present for all of the previous num_hours hours.
    
    Usage:
    Instantiate the class, and run is_device_present() to see if the device
    has responded to pings within that time period

    Inputs:
    device_ip - A string with the device IP, e.g. "192.168.1.1"

    Outputs:
    None
    """

    def __init__(self, device_ip):
        """
        Description:
        Initialization of the alarm_sequence class
        
        Inputs:
        device_ip - See class description

        Outputs:
        None
        """

        self.device_ip = device_ip
        self.initialize_devicetrack_dict()
        self.current_hr = int(time.localtime()[3])-1
        self.stop_flag = threading.Event()
        self.start_ping_loop()
        logging.info("Device tracker successfully initialized")

    def initialize_devicetrack_dict(self):
        """
        Description:
        Initialization of the devicetrack_dict that tracks whether the device
        has responded to pings in the last 24 hours.
        
        Inputs:
        None

        Outputs:
        None
        """

        self.devicetrack = {}
        for i in range(24):
            self.devicetrack[i] = False

    def ping(self):
        """
        Description:
        Function to ping the device located at the initialized IP address.
        
        Inputs:
        None

        Outputs:
        None
        """

        command = "ping -c 10 " + self.device_ip
        result = os.system(f"{command} > /dev/null 2>&1") #Add output suppression to the command
        if result == 0:
            logging.info("Initialized device WAS found on the network.")
            return True
        else:
            logging.info("Initialized device WAS NOT found on the network.")
            return False

    def ping_loop(self):
        """
        Description:
        Function to call the ping function every hour.
        
        Inputs:
        None

        Outputs:
        None
        """

        while(1):
            hr = int(time.localtime()[3])
            if self.current_hr != hr:
                self.devicetrack[hr] = self.ping()
                self.current_hr = hr
            time.sleep(10)

    def start_ping_loop(self):
        """
        Description:
        Starts off a new thread for the ping_loop() function
        
        Inputs:
        None

        Outputs:
        None
        """

        self.ping_thread = threading.Thread(target=self.ping_loop)
        self.ping_thread.start()

    def stop_ping_loop(self):
        """
        Description:
        Stops the thread started by start_ping_loop()
        
        Inputs:
        None

        Outputs:
        None
        """

        self.stop_flag.set()
        self.ping_thread.join()

    def is_device_present(self, trailing_hours = 6):
        """
        Description:
        Checks the self.devicetrack dict to see if the device has been present
        for the last trailing_hours hours
        
        Inputs:
        trailing_hours - number of hours to check for the device being present

        Outputs:
        None
        """

        hr = int(time.localtime()[3])
        for i in range(trailing_hours):
            test_hr = hr - i
            if test_hr < 0:
                test_hr + 24
            if not self.devicetrack[test_hr]:
                logging.debug("Device not present")
                return False
        logging.debug("Device present")
        return True

    def __del__(self):
        """
        Description:
        Destructor for the class, ensures all threads are stopped
        
        Inputs:
        None

        Outputs:
        None
        """

        self.stop_ping_loop()
