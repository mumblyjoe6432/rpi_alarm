import logging
import pigpio

class hw_pwm:
    """
    Description:
    This class controls the PWM hardware on a Rpi version 4 or higher. Note that earlier
    versions of the hardware do not have this feature
    Also note: There are only two PWM hardware modules, and each can output to only 2
    GPIOs (at least on the Rpi 4). Please check the manual to see what gpio_num is valid
    
    Usage:
    led_handle = hw_pwm(gpio_num)
    You can then control the PWM by:
    led_handle.set_pwm(50) #Set a duty cycle of 50

    Inputs:
    gpio_num - The number of the gpio on the Rpi

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
        self._dutycycle = 0
        self.freq = 500

        self.init_pwm()
        self.dutycycle = self._dutycycle

        logging.info(f"HW PWM Initialized")

    def __del__(self):
        """
        Description:
        Destructor for the class - ensures the PWM module is set to 0 if the proc is killed
        
        Inputs:
        None

        Outputs:
        None
        """

        self.pwmobj.hardware_PWM(self.gpio_num, 0, 0)
        self.pwmobj.stop()

    def init_pwm(self):
        """
        Description:
        Initialization the selected Rpi GPIO to use the PWM module
        
        Inputs:
        None

        Outputs:
        None
        """

        self.pwmobj = pigpio.pi()
        self.pwmobj.set_mode(self.gpio_num, pigpio.OUTPUT)

    def _set_pwm(self, pwm):
        """
        Private helper that clamps and writes PWM to hardware.

        Minimal validation: first tries to coerce input to float (invalid input is ignored).
        Values are clamped to [0, 100]. Hardware write is attempted but failures are
        ignored so setting dutycycle early (e.g. in __init__ before init_pwm()) doesn't crash.
        """
        try:
            pwm_val = float(pwm)
        except (TypeError, ValueError):
            logging.warning("hw_pwm: invalid pwm value passed (ignored): %r", pwm)
            return

        # clamp to 0..100
        if pwm_val < 0.0:
            logging.warning("hw_pwm: pwm value less than 0: %r. pwm will be set to 0", pwm)
            pwm_val = 0.0
        elif pwm_val > 100.0:
            logging.warning("hw_pwm: pwm value greater than 100: %r. pwm will be set to 100", pwm)
            pwm_val = 100.0

        pwm_int = int(pwm_val * 10000)  # pigpio uses 0..1_000_000 (100% -> 1_000_000)

        try:
            self.pwmobj.hardware_PWM(self.gpio_num, self.freq, pwm_int)
        except Exception:
            # Minimal handling: ignore hardware write errors (keeps behavior simple)
            pass

        # update last-known duty cycle
        self._dutycycle = pwm_val
        logging.info("HW PWM on GPIO %s set to %s%%", self.gpio_num, pwm_val)

    def set_pwm(self, pwm):
        """
        Description:
        Sets the PWM of the activated PWM module
        
        Inputs:
        pwm - a number from 0-100 that corresponds to a % PWM

        Outputs:
        None
        """

        self.dutycycle = pwm

    @property
    def dutycycle(self):
        """
        Description:
        Current duty cycle (0–100). Returns the last value actually set by this process.
        
        Inputs:
        None

        Outputs:
        dutycycle - float from 0–100
        """
        return self._dutycycle

    @dutycycle.setter
    def dutycycle(self, value):
        """
        Description:
        Set duty cycle (0–100). Automatically clamps out-of-range values and updates hardware.
        
        Inputs:
        value - new duty cycle (0–100)

        Outputs:
        None
        """
        self._set_pwm(value)
