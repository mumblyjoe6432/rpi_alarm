import threading
import logging
import RPi.GPIO as gpio
from queue import Queue
import time

class keypad:
    #This keypad function is meant to be called every 10 ms (or so) as the other keypad function wasn't working properly
    #Still not sure why the other one doesn't work well tbh
    """
    Description:
    This class supports a DIY keypad with 12 keys, 7 pins
    This class is a way to do this by continuously polling the keypad GPIO inputs to see if there has been a
    button press. To do this, it launches its own thread, and then commmunicates with the parent via the
    threading.Event() class
    
    Usage:
    keypad_handle = keypad(keypad_gpio_defs)
    Then, you need to periodically check the queue (about every 10ms) and pop the button presses
    if not keypad_handle.keypad_queue.empty():
       button_that_was_pressed = keypad_handle.keypad_queue.get()

    Inputs:
    pin_dict - a dictionary that defines the RPi outputs connected to the keypad
                Formatting:
                keypad_gpio_defs = {
                        'row1':26,
                        'row2':19,
                        'row3':13,
                        'row4':6,
                        'col1':21,
                        'col2':20,
                        'col3':16
                    }

    Outputs:
    None
    """

    def __init__(self, pin_dict):
        """
        Description:
        Initialization of the keypad class
        
        Inputs:
        pin_dict - see class def

        Outputs:
        None
        """

        self.pin_dict = pin_dict
        self.keypad_queue = Queue()
        self._setup_gpios()
        self.stop_flag = threading.Event()
        logging.info(f"Keypad initialized successfully")

        self._start_thread()

    def __del__(self):
        """
        Description:
        Destructor for the class - ensures the thread is stopped if the process is killed
        
        Inputs:
        None

        Outputs:
        None
        """

        self.stop_thread()

    def _start_thread(self):
        """
        Description:
        Starts the thread that keeps track of the keypad presses. Is run from __init__()
        
        Inputs:
        None

        Outputs:
        None
        """

        #Initialize the keypad_loop thread
        self.keypad_thread = threading.Thread(target=self._keypad_loop)
        self.keypad_thread.start()

    def _setup_gpios(self):
        """
        Description:
        Initialization the Rpi GPIOs using the pin_dict dictionary from __init__()
        
        Inputs:
        None

        Outputs:
        None
        """

        gpio.setup(self.pin_dict['row1'], gpio.OUT)
        gpio.setup(self.pin_dict['row2'], gpio.OUT)
        gpio.setup(self.pin_dict['row3'], gpio.OUT)
        gpio.setup(self.pin_dict['row4'], gpio.OUT)
        gpio.setup(self.pin_dict['col1'], gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.pin_dict['col2'], gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.pin_dict['col3'], gpio.IN, pull_up_down=gpio.PUD_DOWN)

    def _keypad_loop(self):
        """
        Description:
        Checks to see if a button was pressed, row by row using the _check_line() function
        
        Inputs:
        None

        Outputs:
        None
        """

        while(True):
            self._check_line(self.pin_dict['row1'], ["1","2","3"])
            self._check_line(self.pin_dict['row2'], ["4","5","6"])
            self._check_line(self.pin_dict['row3'], ["7","8","9"])
            self._check_line(self.pin_dict['row4'], ["star","0","pound"])
            time.sleep(0.05)

    def _check_line(self, row, characters):
        """
        Description:
        Checks to see if a button was pressed for a specific column. If so, puts that button in the
        keypad_queue
        
        Inputs:
        row - the RPi gpio number of the row to check
        characters - the label of the characters in that row, ex. row 2 = [4,5,6]

        Outputs:
        None
        """

        gpio.output(row, gpio.HIGH)
        time.sleep(0.01)
        if gpio.input(self.pin_dict['col1']) == 1:
            print("col1")
            self.keypad_queue.put(characters[0])
            time.sleep(0.3)
        elif gpio.input(self.pin_dict['col2']) == 1:
            print("col2")
            self.keypad_queue.put(characters[1])
            time.sleep(0.3)
        elif gpio.input(self.pin_dict['col3']) == 1:
            print("col3")
            self.keypad_queue.put(characters[2])
            time.sleep(0.3)
        gpio.output(row, gpio.LOW)

    def stop_thread(self):
        self.stop_flag.set()
        self.keypad_thread.join()

class keypad2:
    """
    ***NOTE: THIS IS NOT WORKING***

    Description:
    This class supports a DIY keypad with 12 keys, 7 pins
    This class is a way to do this by setting interrupts with gpio.add_event_detect(). However,
    after extensive testing, it was determined that this does not work properly for some reason.
    
    Usage:
    keypad_handle = keypad(keypad_gpio_defs, keypad_btn_decode)
    After this, the function should just call the callback function when a button is pressed.

    Inputs:
    pin_dict - a dictionary that defines the RPi outputs connected to the keypad
                Formatting:
                keypad_gpio_defs = {
                        'row1':26,
                        'row2':19,
                        'row3':13,
                        'row4':6,
                        'col1':21,
                        'col2':20,
                        'col3':16
                    }
    callback_function - function from parent to be called when a keypress is detected

    Outputs:
    None
    """

    def __init__(self, pin_dict, callback_function):
        """
        Description:
        Initialization of the keypad class
        
        Inputs:
        pin_dict - see class def
        callback_function - see class def

        Outputs:
        None
        """

        self.pin_dict = pin_dict
        self.callback_function = callback_function
        self.keypad_queue = Queue()
        self.setup_gpios()
        logging.info(f"Keypad initialized successfully")

    def setup_gpios(self):
        """
        Description:
        Initialization the Rpi GPIOs using the pin_dict dictionary from __init__()
        
        Inputs:
        None

        Outputs:
        None
        """

        #Setup the GPIO directions and pullups
        gpio.setup(self.pin_dict['row1'], gpio.OUT)
        gpio.setup(self.pin_dict['row2'], gpio.OUT)
        gpio.setup(self.pin_dict['row3'], gpio.OUT)
        gpio.setup(self.pin_dict['row4'], gpio.OUT)
        gpio.setup(self.pin_dict['col1'], gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.pin_dict['col2'], gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.pin_dict['col3'], gpio.IN, pull_up_down=gpio.PUD_DOWN)

        #Turn on the GPIOs
        gpio.output(self.pin_dict['row1'], gpio.HIGH)
        gpio.output(self.pin_dict['row2'], gpio.HIGH)
        gpio.output(self.pin_dict['row3'], gpio.HIGH)
        gpio.output(self.pin_dict['row4'], gpio.HIGH)
        time.sleep(1)

        #Initialize keypress variable
        self.keypress_active = False

        #Add interrupt sequences
        self.add_event_detects()

    def add_event_detects(self):
        """
        Description:
        Adds event interrupts for each of the input pins
        
        Inputs:
        None

        Outputs:
        None
        """

        gpio.add_event_detect(self.pin_dict['col1'], gpio.RISING, bouncetime=200, callback=self.keypad_column_func)
        gpio.add_event_detect(self.pin_dict['col2'], gpio.RISING, bouncetime=200, callback=self.keypad_column_func)
        gpio.add_event_detect(self.pin_dict['col3'], gpio.RISING, bouncetime=200, callback=self.keypad_column_func)
        logging.info("Added button event interrupts for keypad")

    def reset_row_gpios(self):
        """
        Description:
        Resets the GPIOs to their initial state, ready to detect another press
        
        Inputs:
        None

        Outputs:
        None
        """

        #Turn on the GPIOs
        gpio.output(self.pin_dict['row1'], gpio.HIGH)
        gpio.output(self.pin_dict['row2'], gpio.HIGH)
        gpio.output(self.pin_dict['row3'], gpio.HIGH)
        gpio.output(self.pin_dict['row4'], gpio.HIGH)
        logging.debug("Turned all the row gpio outputs back on")

    def keypad_column_func(self, gpionum):
        """
        Description:
        Decodes the keypress and passes that information to the callback function from __init__()
        
        Inputs:
        None

        Outputs:
        None
        """

        #Turn off the interrupt sequences
        #self.remove_event_detects() Removed because I think this is causing segfaults, instead added keypress_active variable
        if self.keypress_active:
            return
        self.keypress_active = True
        colname = self.get_colnum_from_gpio(gpionum)
        colnum = int(colname[-1])
        logging.debug(f'gpionum = {gpionum}')
        logging.debug(f'colname = {colname}')
        logging.debug(f'colnum = {colnum}')
        
        #Is it row 1?
        gpio.output(self.pin_dict['row1'], gpio.LOW)
        if gpio.input(self.pin_dict[colname]) == 0:
            logging.debug("Detected a row1 press")
            self.reset_row_gpios()
            if colnum == 1:
                self.callback_function('1')
            elif colnum == 2:
                self.callback_function('2')
            elif colnum == 3:
                self.callback_function('3')
            else:
                logging.debug("Unable to determine the button from a row1 press")
            time.sleep(0.5)
            self.keypress_active = False
            return

        #Is it row 2?
        gpio.output(self.pin_dict['row2'], gpio.LOW)
        if gpio.input(self.pin_dict[colname]) == 0:
            logging.debug("Detected a row2 press")
            self.reset_row_gpios()
            if colnum == 1:
                self.callback_function('4')
            elif colnum == 2:
                self.callback_function('5')
            elif colnum == 3:
                self.callback_function('6')
            else:
                logging.debug("Unable to determine the button from a row2 press")
            time.sleep(0.5)
            self.keypress_active = False
            return

        #Is it row 3?
        gpio.output(self.pin_dict['row3'], gpio.LOW)
        if gpio.input(self.pin_dict[colname]) == 0:
            logging.debug("Detected a row3 press")
            self.reset_row_gpios()
            if colnum == 1:
                self.callback_function('7')
            elif colnum == 2:
                self.callback_function('8')
            elif colnum == 3:
                self.callback_function('9')
            else:
                logging.debug("Unable to determine the button from a row3 press")
            time.sleep(0.5)
            self.keypress_active = False
            return
        
        #Is it row 4?
        gpio.output(self.pin_dict['row4'], gpio.LOW)
        if gpio.input(self.pin_dict[colname]) == 0:
            logging.debug("Detected a row4 press")
            self.reset_row_gpios()
            if colnum == 1:
                self.callback_function('star')
            elif colnum == 2:
                self.callback_function('0')
            elif colnum == 3:
                self.callback_function('pound')
            else:
                logging.debug("Unable to determine the button from a row4 press")
            time.sleep(0.5)
            self.keypress_active = False
            return
        
        time.sleep(0.5)
        self.keypress_active = False
        logging.debug("Unable to find what row triggered the button")

    def get_colnum_from_gpio(self, gpionum):
        """
        Description:
        Returns the column number from the gpio that was pressed
        
        Inputs:
        None

        Outputs:
        None
        """

        for key in self.pin_dict:
            if self.pin_dict[key] == gpionum:
                return key
