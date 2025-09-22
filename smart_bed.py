#!/bin/python

"""
Description
This script is a smart alarm designed for a Raspberry Pi, version 4 or higher (Due to hardware PWM requirement)
It supports:
  1) Button
    To turn off the alarm
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
import logging
import pdb
import threading
import subprocess
import psutil
import vlc
import random
import yaml
import signal
from queue import Queue
from evdev import InputDevice, categorize, ecodes, list_devices

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
    gabephone_ip = "192.168.68.50" #IP of the device you would like to track
    sunrise_minutes = 15 #Number of minutes for the sun to "rise" before the alarm goes off
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
        self.keypad_handle = keypad(self.keypad_gpio_defs)

        #Initialize the smileyface button
        self.smiley_handle = toggle_button(self.smiley_button_gpio, self.smiley_button)

        #Initialize the switch
        self.switch1_handle = switch(self.switch1_gpio)

        #LED initialization
        self.led_handle = hw_pwm(self.led_gpio)

        #Cell phone device tracking class
        self.device_tracker_handle = device_tracker(self.gabephone_ip)
        #self.device_tracker_handle._debug_force_devicetrack_true()

        #Alarm class
        self.alarm_handle = alarm_sequence(self.led_handle.set_pwm, self.alarm_activate)

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

            if not self.keypad_handle.keypad_queue.empty():
                self.keypad_btn_decode(self.keypad_handle.keypad_queue.get())

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
            logging.debug("Alarm file not found")
            return
        os.remove(self.cron_alarm_filepath)
        if self.switch1_handle.get_state(): #There is an inversion here, a short means it reads 0
            logging.info("Alarm switch not enabled, alarm disabled")
            return
        if not self.device_tracker_handle.is_device_present():
            logging.info("Device not present, alarm disabled")
            return
        self.alarm_handle.run_sequence(self.sunrise_minutes)
    
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
        
    def keypad_btn_decode(self, btn):
        """
        Description:
        This function and its following functions, are part of the keypad functionality.
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
        func_to_call = getattr(self, f'keypad_btn_{btn}')
        func_to_call()

    def keypad_btn_1(self):
        self.led_handle.set_pwm(10)
        logging.info("Keypad button 1 detected!")
        pass

    def keypad_btn_2(self):
        self.led_handle.set_pwm(20)
        logging.info("Keypad button 2 detected!")
        pass

    def keypad_btn_3(self):
        self.led_handle.set_pwm(30)
        logging.info("Keypad button 3 detected!")
        pass

    def keypad_btn_4(self):
        self.led_handle.set_pwm(40)
        logging.info("Keypad button 4 detected!")
        pass

    def keypad_btn_5(self):
        self.led_handle.set_pwm(50)
        logging.info("Keypad button 5 detected!")
        pass

    def keypad_btn_6(self):
        self.led_handle.set_pwm(60)
        logging.info("Keypad button 6 detected!")
        pass

    def keypad_btn_7(self):
        self.led_handle.set_pwm(70)
        logging.info("Keypad button 7 detected!")
        pass

    def keypad_btn_8(self):
        self.led_handle.set_pwm(80)
        logging.info("Keypad button 8 detected!")
        pass

    def keypad_btn_9(self):
        self.led_handle.set_pwm(90)
        logging.info("Keypad button 9 detected!")
        pass

    def keypad_btn_star(self):
        self.led_handle.set_pwm(100)
        logging.info("Keypad button * detected!")
        pass

    def keypad_btn_0(self):
        self.led_handle.set_pwm(0)
        logging.info("Keypad button 0 detected!")
        pass

    def keypad_btn_pound(self):
        logging.info("Keypad button # detected!")
        pass

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

        self.alarm_active = False
        self.pwm_function = pwm_function
        self.alarm_finish_function = alarm_finish_function
        logging.info("Alarm sequence initialized")

    def run_sequence(self, sunrise_minutes):
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
        self.alarm_active = True
        total_seconds = sunrise_minutes*60
        time_step = total_seconds/100
        #Exponential rise because pwm works better that way
        #pwm_values = range(1,101) #old linear
        pwm_values = np.exp(np.linspace(0, np.log(100), 100))
        for pwm_value in pwm_values:
            logging.debug(f"Setting PWM to {pwm_values}")
            self.pwm_function(pwm_value)
            time.sleep(time_step)
            if not self.alarm_active:
                return
        self.alarm_active = False
        self.alarm_finish_function()

class sound_blaster:
    """
    Description:
    This class controls the sound for the Rpi
    
    Usage:
    music_handle = sound_blaster(music_dir, alarm_filepath)
    You can then control the PWM by:
    led_handle.set_pwm(50) #Set a duty cycle of 50

    Inputs:
    music_dir - The path to a directory with music mp3s
    alarm_filepath - The path to an mp3 with the music for the alarm

    Outputs:
    None
    """

    def __init__(self, music_dir, alarm_filepath):
        """
        Description:
        Initialization of the switch class
        
        Inputs:
        music_dir - The path to a directory with music mp3s
        alarm_filepath - The path to an mp3 with the music for the alarm

        Outputs:
        None
        """

        self.music_dir = music_dir
        self.alarm_filepath = alarm_filepath
        self.instance = vlc.Instance()
        self.media_list_player = self.instance.media_list_player_new()
        self.play_thread = None
        logging.info("Sound controller initialized")

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

    def _play(self, file_list, repeat_count=0, total_playtime=0):
        """
        Description:
        Plays music files in order. Can determine a total time to play or a number of
        repeats of the music
        
        Inputs:
        file_list - A list of the music mp3s
        repeat_count - Number of times to play the music
        total_playtime - Total time to play the music, overrides the repeat_count

        Outputs:
        None
        """

        total_duration = 0
        self.media_list = self.instance.media_list_new()
        self.media_list_player.set_media_list(self.media_list)
        for file_path in file_list:
            media = self.instance.media_new(file_path)
            self.media_list.add_media(media)
            total_duration += media.get_duration() / 1000  # Duration in seconds

        self.media_list_player.set_playback_mode(vlc.PlaybackMode.loop)  # Set loop mode
        self.media_list_player.play()

        if total_playtime > 0:
            # If total playtime is set, just wait for that total playtime
            time.sleep(total_playtime)
        elif repeat_count > 0:
            # If repeat_count is set, wait for the total duration of the playlist multiplied by the repeat count
            time.sleep(total_duration * repeat_count)

    def play_files(self, file_list, shuffle=False, repeat_count=0, total_playtime=0):
        """
        Description:
        Starts the thread that plays music
        
        Inputs:
        file_list - A list of the music mp3s
        shuffle - Will shuffle the music if True
        repeat_count - Number of times to play the music
        total_playtime - Total time to play the music, overrides the repeat_count

        Outputs:
        None
        """

        if shuffle:
            random.shuffle(file_list)
        if not self.play_thread or not self.play_thread.is_alive():
            logging.info(f"Started the music player")
            self.play_thread = threading.Thread(target=self._play, args=(file_list, repeat_count, total_playtime))
            self.play_thread.start()

    def stop(self):
        """
        Description:
        Stops the thread that is playing music
        
        Inputs:
        None

        Outputs:
        None
        """

        logging.info(f"Stopped the music player")
        self.media_list_player.stop()

    def is_playing(self):
        """
        Description:
        Stops the thread that is playing music
        
        Inputs:
        None

        Outputs:
        True if music is playing, False if not
        """

        return self.media_list_player.get_state() == vlc.State.Playing
    
    def play_directory(self, directory, shuffle=True):
        """
        Description:
        Plays music from a directory
        
        Inputs:
        directory - A directory with only mp3 files inside to be played
        shuffle - True if random order is desired

        Outputs:
        None
        """

        song_filenames = os.listdir(directory)
        song_filepaths = []
        for song_filename in song_filenames:
            song_filepaths.append(directory + '/' + song_filename)
        self.play_files(song_filepaths, shuffle=shuffle)
        logging.info(f"Music started from directory {directory}")

    def play_music_dir(self):
        """
        Description:
        Plays the music from the music_dir that was specified when the class
        was instantiated
        
        Inputs:
        None

        Outputs:
        None
        """

        logging.info(f"Playing music")
        self.play_directory(self.music_dir)

    def play_alarm(self):
        """
        Description:
        Plays the file that was specified as the alarm_filepath when the
        class was instantiated
        
        Inputs:
        None

        Outputs:
        None
        """

        logging.info(f"Playing alarm sound")
        self.play_files([self.alarm_filepath], total_playtime=3600)

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
        self.dutycycle = 0
        self.freq = 500

        self.init_pwm()
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

    def set_pwm(self, pwm):
        """
        Description:
        Sets the PWM of the activated PWM module
        
        Inputs:
        pwm - a number from 0-100 that corresponds to a % PWM

        Outputs:
        None
        """

        #pwm is a float from 0-100
        logging.info(f"PWM set to {pwm}%%")
        pwm_int = int(pwm*10000)
        self.pwmobj.hardware_PWM(self.gpio_num, self.freq, pwm_int)

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

class mini_keyboard:
    #The mini-keybaord controller class controlls the mini keyboard. Presumably it works with many types, but
    #the type it was tested for is:
    #https://www.amazon.com/dp/B09Z613J78?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1
    """
    Description:
    This class supports a mini keyboard with any number of keys
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

if __name__ == "__main__":
    smart_bed()
