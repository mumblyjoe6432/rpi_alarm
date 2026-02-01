import RPi.GPIO as gpio
import threading
import logging
import time
from queue import Queue

class toggle_button:
    """
    Description:
    #This function is meant to report when a button is pressed. Connect your button to the gpio given in
    #__init__ and gnd.
    
    Usage:
    button_handle = toggle_button(gpio_number, button_type)
    Then, you need to periodically check the queue (about every 10ms) and pop the button presses
    if not button_handle.button_queue.empty():
       keypad_handle.keypad_queue.get()

    Inputs:
    gpio_num - the number of the gpio on the Rpi
    button_type = Either 'normally_open' or 'normally_closed'. The class will update the queue
                  when the state indicates the button has been pressed. If not used, will default
                  to "normally open" as most buttons are

    Outputs:
    None
    """

    def __init__(self, gpio_num, button_type="normally_open"):
        """
        Description:
        Initialization of the toggle_button class
        
        Inputs:
        gpio_num - see class def
        button_type - see class def

        Outputs:
        None
        """

        self.gpio_num = gpio_num
        self.button_type = button_type
        self.toggle_button_queue = Queue()
        self._setup_gpios()
        self.stop_flag = threading.Event()
        logging.info(f"Toggle button initialized successfully")

        self._start_thread()

    def __del__(self):
        """
        Description:
        Destructor for the class, ensures all threads are stopped
        
        Inputs:
        None

        Outputs:
        None
        """

        self._stop_thread()


    def _setup_gpios(self):
        """
        Description:
        Initialization the Rpi GPIOs using the gpio_num variable
        
        Inputs:
        None

        Outputs:
        None
        """

        gpio.setup(self.gpio_num, gpio.IN, pull_up_down=gpio.PUD_UP)

    def _start_thread(self):
        """
        Description:
        Starts the thread that keeps track of the button presses. Is run from __init__()
        
        Inputs:
        None

        Outputs:
        None
        """

        #Initialize the button state
        if self.button_type == "normally_closed":
            self.button_state = 0
        else:
            self.button_state = 1

        #Initialize the toggle_button_loop thread
        self.button_thread = threading.Thread(target=self._toggle_button_loop)
        self.button_thread.start()

    def _toggle_button_loop(self):
        """
        Description:
        Checks to see if a button was pressed
        
        Inputs:
        None

        Outputs:
        None
        """

        new_button_state = gpio.input(self.gpio_num)
        if new_button_state == self.button_state:
            pass
        elif self.button_type == 'normally_open' and new_button_state == 0:
            self.keypad_queue.put("Press")
            self.button_state = 0
        elif self.button_type == 'normally_closed' and new_button_state == 1:
            self.keypad_queue.put("Press")
            self.button_state = 1

        time.sleep(0.02)

    def _stop_thread(self):
        self.stop_flag.set()
        self.button_thread.join()

class toggle_button2:
    """
    #This function relies on the gpio.add_event_detect() function that is, at best, unreliable. DO NOT USE
    #I left it here in case we figure out how to make this functionality more reliable

    Description:
    #Button that changes the state from 0->1 or 1->0 on each press (so we need to detect an event for both)
    
    Usage:
    button_handle = toggle_button(gpio_number, callback_function)

    Inputs:
    gpio_num - the number of the gpio on the Rpi
    callback_function - pointer to a function in the parent that will be called when the button is triggered

    Outputs:
    None
    """

    def __init__(self, gpio_num, callback_function):
        """
        Description:
        Initialization of the toggle_button class
        
        Inputs:
        gpio_number - see class def
        callback_function - see class def

        Outputs:
        None
        """

        self.gpio_num = gpio_num
        self.callback_function = callback_function
        self.setup_gpio()
        logging.info(f"Button initialized on GPIO{gpio_num}")

    def setup_gpio(self):
        """
        Description:
        Initialization of the gpio and event detect interrupt
        
        Inputs:
        None

        Outputs:
        None
        """

        #Setup the GPIO direction
        gpio.setup(self.gpio_num, gpio.IN, pull_up_down=gpio.PUD_UP)
        gpio.add_event_detect(self.gpio_num, gpio.BOTH, bouncetime=2000, callback=self.callback_function)