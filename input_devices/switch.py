import RPi.GPIO as gpio
import logging

class switch:
    """
    Description:
    #Class to handle a toggle switch
    #It doesn't have any active polling or detect a change in state, but instead is used by
    #calling the get_state() function to see if it is "on" or "off"
    
    Usage:
    switch_handle = switch(gpio_number)

    Inputs:
    gpio_num - the number of the gpio on the Rpi

    Outputs:
    None
    """

    def __init__(self, gpio_num):
        """
        Description:
        Initialization of the switch class
        
        Inputs:
        gpio_num - see class def

        Outputs:
        None
        """

        self.gpio_num = gpio_num
        self.setup_gpio()
        logging.info(f"Switch initialized on GPIO{gpio_num}")

    def setup_gpio(self):
        """
        Description:
        Initialization the Rpi GPIOs using the pin_dict class from __init__()
        
        Inputs:
        None

        Outputs:
        None
        """

        #Setup the GPIO direction
        gpio.setup(self.gpio_num, gpio.IN, pull_up_down=gpio.PUD_UP)

    def get_state(self):
        """
        Description:
        Function to return the state of the gpio
        
        Inputs:
        None

        Outputs:
        state - either a 1 or a 0
        """

        return gpio.input(self.gpio_num)
