#!/bin/python

"""
Description
This script is a smart alarm designed for a Raspberry Pi, version 4 or higher (Due to hardware PWM requirement)
It supports:
  1) Button
    To turn off the alarm
    Note: I have actually disabled this in favor of using any USB keyboard button. The class is still there
  2) Keypad
    Standard 12-key 7pin DIY keyboard (currently disabled, because the USB keyboards are better y'all)
  3) Sound
    You can play songs stored on the device if they're in a particular directory, it also supports the alarm bell obviously
  4) USB Keyboard
    I found this really cool USB keyboard with not only 12 buttons but 2 dials (perfect for light and volume control)
  5) Dimmable LED controller
    Note this is *not* a driver, the RPi does not have enough power for that
  6) Device tracker
    If you want, you can have the alarm go off only if a device (like your cell phone) is found on the wifi. The script
    will ping the IP given. However, if you turn off the device, the alarm will not go off.
  7) Switch support
    Currently using a switch to turn on/off the alarm
    Note: This is now no longer part of the code, but the class is available to use
  8) Alarm algorithm
    The current alarm algorithm will start bringing up the lights a set period before the actual alarm sounds
    ideally simulating a sunrise

Usage
This script is designed to be run by the regular user at boot. To get the alarm to start, you need to create
an empty file title "startalarm.start" in the directory specified

Author
Gabe Thompson

Creation Date
August 23, 2014
"""

import RPi.GPIO as gpio
import numpy as np
import pigpio
import time, os
import math
import logging
import pdb
import threading
import vlc
import random
import yaml
import signal
from queue import Queue
from evdev import InputDevice, categorize, ecodes, list_devices
from collections import deque

#Local Module Imports
from input_devices.keypad import keypad
from input_devices.switch import switch
from input_devices.toggle_button import toggle_button
from input_devices.mini_keyboard import mini_keyboard
from output_devices.sound_blaster import sound_blaster
from rpi_helpers.device_tracker import device_tracker
from rpi_helpers.hw_pwm import hw_pwm

class smart_bed:
    """
    Description:
    This is the main smart_bed class. It controls the lights, sound system
    
    Usage:
    Make sure the proper global variables are set, then interact with the RPi with
    the proper periphrials.

    Inputs:
    None

    Outputs:
    None
    """

    #GENERAL CONFIG VARIABLES
    logfile_filepath = "/home/gabe/.smartbed/smart_bed.log" #Location of the main log file
    cron_alarm_filepath = "/home/gabe/.smartbed/startalarm.start" #Location of the empty file created by cron when the alarm should start
    myphone_ip = "192.168.68.50" #IP of the device you would like to track
    sunrise_minutes = 15 #Number of minutes for the sun to "rise" before the alarm goes off
    alarm_volume = 50 #Volume of the alarm, out of 100
    music_dir = "/home/gabe/Music/music_playlist" #Directory of the music to play
    alarm_filepath = "/home/gabe/Music/alarms/soft_naturey_song.mp3" #File location for the alarm song

    #GPIO CONFIG VARIABLES
    keypad_gpio_defs = { #Keypad connections to the GPIO
            'row1':26,
            'row2':19,
            'row3':13,
            'row4':6,
            'col1':21,
            'col2':20,
            'col3':16
        }
    smiley_button_gpio = 1 #GPIO that the smiley button is connected to (this is the button that turns off the alarm)
    switch1_gpio = 25 #GPIO that the switch is connected to (This switch turns off the alarm)
    led_gpio = 18 #GPIO that controls the lights. Must be a PWM GPIO
    mini_keyboard_device_name = "USB Composite Device Keyboard"
    brightness_step = 1
    volume_step = 1
    mini_keyboard_last_five = deque(maxlen=5)
    alarm_disable_soft = False
    _last_brightness = 50

    def __init__(self):
        """
        Description:
        This is the initializer for the main smart_bed class.
        
        Usage:
        Instantiate the class

        Inputs:
        None

        Outputs:
        None
        """
        
        #Initialize the logger
        logging.basicConfig(level=logging.INFO, filename=self.logfile_filepath, format='%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s: %(message)s')
        logging.info("*********************")
        logging.info("*********************")
        logging.info("RASPBERRY PI REBOOTED")
        ct = time.localtime()
        logging.info("%s/%s/%s %s:%s:%s"%(ct[1], ct[2], ct[0], ct[3], ct[4], ct[5]))
        logging.info("*********************")
        logging.info("*********************")
        logging.info("Log Started")
        logging.info(f"The PID is {os.getpid()}")

        #***********************************************
        #IMPORTANT FILE LOCATIONS
        #File that cron will create when the alarm is set via cron
        #Maybe one day just integrate into a cfg file?
        logging.info(f"cron_alarm file located at {self.cron_alarm_filepath}")

        #***********************************************
        #GPIO SECTION
        #Initialization stuff
        #gpio.cleanup()
        gpio.setwarnings(False)
        gpio.setmode(gpio.BCM)

        #***********************************************
        #CLASS INITIALIZATION
        #Initialize the keypad class
        #self.keypad_handle = keypad(self.keypad_gpio_defs) #Removed this in favor of the mini_keyboard

        #Initialize the mini keyboard class
        self.mini_keyboard_handle = mini_keyboard(self.mini_keyboard_device_name)

        #Initialize the smileyface button
        #self.smiley_handle = toggle_button(self.smiley_button_gpio, self.smiley_button) #Removed this in favor of the mini_keyboard

        #Initialize the switch
        #self.switch1_handle = switch(self.switch1_gpio) #Removed this in favor of the mini_keyboard

        #LED initialization
        self.led_handle = hw_pwm(self.led_gpio)

        #Cell phone device tracking class
        self.device_tracker_handle = device_tracker(self.myphone_ip)
        #self.device_tracker_handle._debug_force_devicetrack_true()

        #Alarm class
        #self.alarm_handle = alarm_sequence(self.led_handle.set_pwm, self.alarm_activate)
        self.alarm_handle = alarm_sequence(self.brightness_set, self.alarm_activate)

        #Music class
        self.music_handle = sound_blaster(self.music_dir, self.alarm_filepath)

        self.mainloop()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def mainloop(self):
        """
        Description:
        This is the main loop function. Every 10ms it loops through to check whether it should start
        the alarm or handle a keypad button press
        
        Usage:
        This is run via the __init__() function, so no user intervention is needed

        Inputs:
        None

        Outputs:
        None
        """
        
        logging.info("Main loop begin")
        #Blink lights to show that we're starting the main loop
        self.blink_lights()

        while(True):
            time.sleep(0.01)

            # if not self.keypad_handle.keypad_queue.empty(): #Removing in favor of the mini_keyboard
            #     self.button_decode('keypad', self.keypad_handle.keypad_queue.get())

            if not self.mini_keyboard_handle.keypad_queue.empty():
                if self.alarm_handle.is_running():
                    self.alarm_handle.stop()
                self.button_decode('mini_keyboard', self.mini_keyboard_handle.keypad_queue.get())

            #See if we need to ping the cell phone
            # self.device_tracker_handle.update_devicetrack_if_necessary()

            #See if we should start the alarm
            self.check_alarm()
            pass

    def signal_handler(self):
        """
        Description:
        This is a function that runs when the main_loop() is killed. It is intended
        to help kill threads and prevent runaway threads.
        
        Usage:
        This is run via the __init__() function, so no user intervention is needed

        Inputs:
        None

        Outputs:
        None
        """

        self.keypad_handle.stop_thread()
        self.device_tracker_handle.stop_ping_loop()

    def blink_lights(self):
        """
        Description:
        This function is designed to let the user know when the Rpi has booted. Just
        before running the loop of the main loop, this function is run to blink the
        lights.
        
        Usage:
        This is run via the main_loop() function, so no user intervention is needed

        Inputs:
        None

        Outputs:
        None
        """
        self.led_handle.set_pwm(0)
        time.sleep(0.1)
        self.led_handle.set_pwm(2)
        time.sleep(0.1)
        self.led_handle.set_pwm(0)

    def alarm_activate(self):
        """
        Description:
        This function simply plays the alarm sound.
        
        Usage:
        The function is forwarded to the alarm controller as a pointer, so it
        is actually run by the alarm_sequence class

        Inputs:
        None

        Outputs:
        None
        """
        self.volume_set(self.alarm_volume)
        self.music_handle.play_alarm()

    def check_alarm(self):
        """
        Description:
        This function checks to see if the alarm should be run. First, it checks
        for the cron_alarm_filepath file. If it exists, it then checks the alarm
        disable switch. Then, it checks whether the IP device is present. If all
        these conditions are met, it will run the alarm sequence
        
        Usage:
        This is run via the main_loop() function, so no user intervention is needed

        Inputs:
        None

        Outputs:
        None
        """
        if not os.path.isfile(self.cron_alarm_filepath):
            #logging.debug("Alarm file not found")
            return
        os.remove(self.cron_alarm_filepath)
        # I removed the alarm disable switch due to only wanting the keypad visible
        # if self.switch1_handle.get_state(): #There is an inversion here, a short means it reads 0
        #     logging.info("Alarm switch not enabled, alarm disabled")
        #     return
        if self.alarm_disable_soft:
            logging.info("Soft alarm disable engaged, alarm disabled")
            return
        # if not self.device_tracker_handle.is_device_present():
        #     logging.info("Device not present, alarm disabled")
        #     return
        self.alarm_handle.start_alarm_sequence(self.sunrise_minutes)
    
    def smiley_button(self, gpio_num):
        """
        Description:
        This function is run when the smiley button is pressed :)
        
        Usage:
        It is run as part of the toggle button class.

        Inputs:
        None

        Outputs:
        None
        """
        logging.info("Smiley button detected!")
        if self.alarm_handle.alarm_active:
            self.alarm_handle.alarm_active = False
            return
        if self.music_handle.is_playing():
            self.music_handle.stop()
            return
        self.music_handle.play_music() #Gabe commented out because button is too touchy and music kept turning on
        pass
        
    def button_decode(self, source, btn):
        """
        Description:
        This function and its following functions, are part of the keypad/mini
        keyboard functionality.
        If a button is pressed, this function points it to the correct following
        functions based on what button it was, so that the correct function can be
        selected.
        
        Usage:
        This is run via the main_loop() function, so no user intervention is needed

        Inputs:
        None

        Outputs:
        None
        """
        if source == "keypad":
            func_to_call = getattr(self, f'keypad_btn_{btn}')
        elif source == "mini_keyboard":
            if self.alarm_handle.is_running():
                self.alarm_handle.stop()
                return
            func_to_call = getattr(self, f'mini_keyboard_{btn}')
            self.mini_keyboard_stack_update(btn)
        else:
            logging.warning(f"No handler defined for {func_name}")
            return
        func_to_call()

    # ================================
    # Keypad Handlers
    # ================================

    def keypad_btn_1(self):
        self.brightness_set(10)
        logging.info("Keypad button 1 detected!")
        pass

    def keypad_btn_2(self):
        self.brightness_set(20)
        logging.info("Keypad button 2 detected!")
        pass

    def keypad_btn_3(self):
        self.brightness_set(30)
        logging.info("Keypad button 3 detected!")
        pass

    def keypad_btn_4(self):
        self.brightness_set(40)
        logging.info("Keypad button 4 detected!")
        pass

    def keypad_btn_5(self):
        self.brightness_set(50)
        logging.info("Keypad button 5 detected!")
        pass

    def keypad_btn_6(self):
        self.brightness_set(60)
        logging.info("Keypad button 6 detected!")
        pass

    def keypad_btn_7(self):
        self.brightness_set(70)
        logging.info("Keypad button 7 detected!")
        pass

    def keypad_btn_8(self):
        self.brightness_set(80)
        logging.info("Keypad button 8 detected!")
        pass

    def keypad_btn_9(self):
        self.brightness_set(90)
        logging.info("Keypad button 9 detected!")
        pass

    def keypad_btn_star(self):
        self.brightness_set(100)
        logging.info("Keypad button * detected!")
        pass

    def keypad_btn_0(self):
        self.brightness_set(0)
        logging.info("Keypad button 0 detected!")
        pass

    def keypad_btn_pound(self):
        logging.info("Keypad button # detected!")
        pass

    # ================================
    # Mini Keyboard Handlers
    # ================================

    def mini_keyboard_R1C1(self):
        logging.info("Mini keyboard: R1C1 pressed")
        pass

    def mini_keyboard_R1C2(self):
        logging.info("Mini keyboard: R1C2 pressed")
        pass

    def mini_keyboard_R1C3(self):
        logging.info("Mini keyboard: R1C3 pressed")
        pass

    def mini_keyboard_R2C1(self):
        logging.info("Mini keyboard: R2C1 pressed")
        pass

    def mini_keyboard_R2C2(self):
        logging.info("Mini keyboard: R2C2 pressed")
        pass

    def mini_keyboard_R2C3(self):
        logging.info("Mini keyboard: R2C3 pressed")
        pass

    def mini_keyboard_R3C1(self):
        logging.info("Mini keyboard: R3C1 pressed")
        pass

    def mini_keyboard_R3C2(self):
        logging.info("Mini keyboard: R3C2 pressed")
        pass

    def mini_keyboard_R3C3(self):
        logging.info("Mini keyboard: R3C3 pressed")
        pass

    def mini_keyboard_R4C1(self):
        logging.info("Mini keyboard: R4C1 pressed")
        pass

    def mini_keyboard_R4C2(self):
        logging.info("Mini keyboard: R4C2 pressed")
        pass

    def mini_keyboard_R4C3(self):
        logging.info("Mini keyboard: R4C3 pressed")
        pass

    # Dials
    def mini_keyboard_dial_left_up(self):
        logging.info("Mini keyboard: Left dial turned up")
        self.volume_up()
        pass

    def mini_keyboard_dial_left_down(self):
        logging.info("Mini keyboard: Left dial turned down")
        self.volume_down()
        pass

    def mini_keyboard_dial_left_press(self):
        logging.info("Mini keyboard: Left dial pressed")
        if self.music_handle.is_playing():
            self.music_handle.stop()
        else:
            self.volume_toggle()
        pass

    def mini_keyboard_dial_right_up(self):
        logging.info("Mini keyboard: Right dial turned up")
        self.brightness_up()
        pass

    def mini_keyboard_dial_right_down(self):
        logging.info("Mini keyboard: Right dial turned down")
        self.brightness_down()
        pass

    def mini_keyboard_dial_right_press(self):
        logging.info("Mini keyboard: Right dial pressed")
        self.brightness_toggle()
        pass

    def brightness_up(self, step=None):
        """
        Description:
        Increase LED brightness by `step` percent.
        If step is None, use self.brightness_step.
        """
        if step is None:
            step = self.brightness_step
        self.led_handle.dutycycle = self.led_handle.dutycycle + step

    def brightness_down(self, step=None):
        """
        Description:
        Decrease LED brightness by `step` percent.
        If step is None, use self.brightness_step.
        """
        if step is None:
            step = self.brightness_step
        self.led_handle.dutycycle = self.led_handle.dutycycle - step

    def brightness_set(self, level):
        """
        Description:
        Set LED brightness directly (0–100).
        """
        self.led_handle.dutycycle = level

    def brightness_toggle(self):
        """
        Description:
        Toggle LED brightness on/off.
        When turning off, remembers the last nonzero brightness level.
        When turning back on, restores that level.
        """

        if self.led_handle.dutycycle > 0:
            # Lights are on -> turn off
            self._last_brightness = self.led_handle.dutycycle
            self.led_handle.dutycycle = 0
            logging.info(f"Brightness toggled OFF (saved {self._last_brightness}%)")
        else:
            # Lights are off -> restore last brightness
            restore_level = self._last_brightness
            self.led_handle.dutycycle = restore_level
            logging.info(f"Brightness toggled ON (restored {restore_level}%)")

    def volume_up(self, step=None):
        """
        Description:
        Increase volume by `step` percent.
        If step is None, use self.volume_step.
        """
        if step is None:
            step = self.volume_step
        self.music_handle.volume = self.music_handle.volume + step

    def volume_down(self, step=None):
        """
        Description:
        Decrease volume by `step` percent.
        If step is None, use self.volume_step.
        """
        if step is None:
            step = self.volume_step
        self.music_handle.volume = self.music_handle.volume - step

    def volume_set(self, level):
        """
        Description:
        Set volume directly (0–100).
        """
        self.music_handle.volume = level

    def volume_toggle(self):
        """
        Description:
        Toggle volume on/off.
        When turning off, remembers the last nonzero volume level.
        When turning back on, restores that level.
        """
        if self.music_handle.volume > 0:
            self._last_volume = self.music_handle.volume
            self.music_handle.volume = 0
            logging.info(f"Volume muted (saved {self._last_volume}%)")
        else:
            restore_level = self._last_volume
            self.music_handle.volume = restore_level
            logging.info(f"Volume unmuted (restored {restore_level}%)")

    def mini_keyboard_stack_update(self, btn):
        """
        Description:
        Mechanism for recognizing simple input patters on the mini keyboard.

        Usage:
        This function is called after a button press is recognized and decoded.
        It updates the self.mini_keyboard_last_five and then checks against patterns.

        Inputs:
        btn - The string that corresponds to the button pressed

        Outputs:
        None
        """

        self.mini_keyboard_last_five.appendleft(btn)
        logging.debug(f"The current stack is {list(self.mini_keyboard_last_five)}")

        #Patterns to recognize

        #Disable the alarm
        if list(self.mini_keyboard_last_five) == ['R4C3', 'R2C2', 'R1C3', 'R1C1', 'R3C1']:
            logging.info(f"Arm alarm pattern recognized")
            self.alarm_disable_soft = False
            #Blink 3 times to let the user know the command was received
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()

        #Enable the alarm
        if list(self.mini_keyboard_last_five) == ['R4C1', 'R2C2', 'R1C3', 'R1C1', 'R3C1']:
            logging.info(f"Disarm alarm pattern recognized")
            self.alarm_disable_soft = True
            #Blink 2 times to let the user know the command was received
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()
            time.sleep(0.5)
            self.brightness_toggle()

class alarm_sequence:
    """
    Description:
    This class controls the alarm sequence. Initialize by giving the two required
    functions, then when required, runs the alarm sequence.
    
    Usage:
    Instantiate the class, and run run_sequence() when you want the alarm
    sequence to start.

    Inputs:
    pwm_function - The pointer to the function to control the pwm, specifically
                   hw_pwm.set_pwm()
    alarm_finish_function - The pointer to a function to run when the alarm
                            finishes. sound_blaster.play_alarm() is a good
                            suggestion.

    Outputs:
    None
    """

    stop_thread = False
    pwm_function = None
    alarm_finish_function = None
    alarm_thread = None

    def __init__(self, pwm_function, alarm_finish_function):
        """
        Description:
        Initialization of the alarm_sequence class
        
        Inputs:
        pwm_function - See class description
        alarm_finish_function - See class description

        Outputs:
        None
        """

        self.pwm_function = pwm_function
        self.alarm_finish_function = alarm_finish_function
        logging.info("Alarm sequence initialized")

    def __del__(self):
        """
        Description:
        Destructor for the class, ensures all threads are stopped
        
        Inputs:
        None

        Outputs:
        None
        """

        self.stop()

    def _alarm_sequence(self, sunrise_minutes):
        """
        Description:
        Function to run the alarm sequence. Will slowly ramp up
        the LED intensity over the sunrise_minutes time frame,
        then it will run the alarm_finish_function
        
        Inputs:
        sunrise_minutes - number of minutes over which to ramp
                          the LED intensity

        Outputs:
        None
        """

        logging.debug("Running alarm sequence")

        #Break the sleep times into parts to only sleep for max 1 second
        #This makes it so we can stop the thread quickly
        total_seconds = sunrise_minutes*60
        time_step = total_seconds/100
        time_step_int = int(math.floor(time_step))
        time_step_remainder = time_step - time_step_int

        #Exponential rise because pwm works better that way
        #pwm_values = range(1,101) #old linear
        pwm_values = np.exp(np.linspace(0, np.log(100), 100))
        for pwm_value in pwm_values:
            logging.debug(f"Setting PWM to {pwm_value}")
            self.pwm_function(pwm_value)

            for i in range(time_step_int):
                if self.stop_thread:
                    return
                time.sleep(1)

            if self.stop_thread:
                return

            time.sleep(time_step_remainder)

        self.alarm_finish_function()

    def start_alarm_sequence(self, sunrise_minutes=15):
        """
        Description:
        Function to kick off the alarm sequence. Is just a wrapper
        for the function _alarm_sequence that kicks off a thread.
        
        Inputs:
        sunrise_minutes - number of minutes over which to ramp
                          the LED intensity

        Outputs:
        None
        """

        self.stop_thread = False
        if self.alarm_thread != None:
            if self.alarm_thread.is_alive():
                logging.warning(f"Alarm start was triggered, but the alarm thread is already running")
                return
        logging.info(f"Started the alarm sequence thread")
        self.alarm_thread = threading.Thread(target=self._alarm_sequence, args=(sunrise_minutes,))
        self.alarm_thread.start()

    def stop(self):
        """
        Description:
        Stops the alarm sequence thread immediately
        
        Inputs:
        None

        Outputs:
        None
        """

        self.stop_thread = True

    def is_running(self):
        """
        Description:
        Asks if alarm sequence thread is running
        
        Inputs:
        None

        Outputs:
        True if alarm sequence thread is running, False if not
        """

        if self.alarm_thread == None:
            return False

        return self.alarm_thread.is_alive()

if __name__ == "__main__":
    smart_bed()
