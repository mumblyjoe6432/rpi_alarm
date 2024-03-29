#!/bin/python

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

class smart_bed:
    def __init__(self):
        #Initialize the logger
        self.logfile_filepath = "/home/gabe/.smartbed/smart_bed.log"
        logging.basicConfig(level=logging.INFO, filename=self.logfile_filepath, format='%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s: %(message)s')
        logging.info("Log Started")
        logging.info(f"The PID is {os.getpid()}")

        #***********************************************
        #IMPORTANT FILE LOCATIONS
        #File that cron will create when the alarm is set via cron
        #Maybe one day just integrate into a cfg file?
        self.cron_alarm_filepath = "/home/gabe/.smartbed/startalarm.start"
        logging.info(f"cron_alarm file located at {self.cron_alarm_filepath}")

        #***********************************************
        #OTHER VARIABLES
        #Cellphone IP
        self.gabephone_ip = "192.168.68.50"
        self.sunrise_minutes = 15
        self.sexy_music_dir = "/home/gabe/Music/sexy_music"
        self.alarm_filepath = "/home/gabe/Music/alarms/soft_naturey_song.mp3"

        #***********************************************
        #GPIO SECTION
        #Initialization stuff
        #gpio.cleanup()
        gpio.setwarnings(False)
        gpio.setmode(gpio.BCM)

        #Define GPIOs
        self.keypad_gpio_defs = {
            'row1':26,
            'row2':19,
            'row3':13,
            'row4':6,
            'col1':21,
            'col2':20,
            'col3':16
        }
        self.smiley_button_gpio = 1
        self.switch1_gpio = 25
        self.led_gpio = 18

        #***********************************************
        #CLASS INITIALIZATION        
        #Initialize the keypad class
        self.keypad_handle = keypad(self.keypad_gpio_defs, self.keypad_btn_decode)

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
        self.music_handle = sound_blaster(self.sexy_music_dir, self.alarm_filepath)

        self.mainloop()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def mainloop(self):
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
        self.keypad_handle.stop_thread()
        self.device_tracker_handle.stop_ping_loop()

    def blink_lights(self):
        self.led_handle.set_pwm(0)
        time.sleep(0.1)
        self.led_handle.set_pwm(2)
        time.sleep(0.1)
        self.led_handle.set_pwm(0)

    def alarm_activate(self):
        self.music_handle.play_alarm()

    def check_alarm(self):
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
        logging.info("Smiley button detected!")
        if self.alarm_handle.alarm_active:
            self.alarm_handle.alarm_active = False
            return
        if self.music_handle.is_playing():
            self.music_handle.stop()
            return
        self.music_handle.play_sexy_music()
        pass
        
    def keypad_btn_decode(self, btn):
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
    def __init__(self, device_ip):
        self.device_ip = device_ip
        self.initialize_devicetrack_dict()
        self.current_hr = int(time.localtime()[3])-1
        self.stop_flag = threading.Event()
        self.start_ping_loop()
        logging.info("Device tracker successfully initialized")

    def initialize_devicetrack_dict(self):
        self.devicetrack = {}
        for i in range(24):
            self.devicetrack[i] = False

    def _debug_force_devicetrack_true(self):
        for i in range(24):
            self.devicetrack[i] = True

    def ping(self):
        command = "ping -c 10 " + self.device_ip
        result = os.system(f"{command} > /dev/null 2>&1") #Add output suppression to the command
        if result == 0:
            logging.info("Initialized device WAS found on the network.")
            return True
        else:
            logging.info("Initialized device WAS NOT found on the network.")
            return False

    def ping_loop(self):
        while(1):
            hr = int(time.localtime()[3])
            if self.current_hr != hr:
                self.devicetrack[hr] = self.ping()
                self.current_hr = hr
            time.sleep(10)

    def start_ping_loop(self):
        self.ping_thread = threading.Thread(target=self.ping_loop)
        self.ping_thread.start()

    def stop_ping_loop(self):
        self.stop_flag.set()
        self.ping_thread.join()

    def is_device_present(self, trailing_hours = 6):
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

class alarm_sequence:
    def __init__(self, pwm_function, alarm_finish_function):
        self.alarm_active = False
        self.pwm_function = pwm_function
        self.alarm_finish_function = alarm_finish_function
        logging.info("Alarm sequence initialized")

    def run_sequence(self, sunrise_minutes):
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
    def __init__(self, sexy_music_dir, alarm_filepath):
        self.sexy_music_dir = sexy_music_dir
        self.alarm_filepath = alarm_filepath
        self.instance = vlc.Instance()
        self.media_list_player = self.instance.media_list_player_new()
        self.play_thread = None
        logging.info("Sound controller initialized")

    def _play(self, file_list, repeat_count=0, total_playtime=0):
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
        if shuffle:
            random.shuffle(file_list)
        if not self.play_thread or not self.play_thread.is_alive():
            logging.info(f"Started the music player")
            self.play_thread = threading.Thread(target=self._play, args=(file_list, repeat_count, total_playtime))
            self.play_thread.start()

    def stop(self):
        logging.info(f"Stopped the music player")
        self.media_list_player.stop()

    def is_playing(self):
        return self.media_list_player.get_state() == vlc.State.Playing
    
    def play_directory(self, directory, shuffle=True):
        song_filenames = os.listdir(directory)
        song_filepaths = []
        for song_filename in song_filenames:
            song_filepaths.append(directory + '/' + song_filename)
        self.play_files(song_filepaths, shuffle=shuffle)
        logging.info(f"Music started from directory {directory}")

    def play_sexy_music(self):
        logging.info(f"Playing sexy music")
        self.play_directory(self.sexy_music_dir)

    def play_alarm(self):
        logging.info(f"Playing alarm sound")
        self.play_files([self.alarm_filepath], total_playtime=3600)

class hw_pwm:
    def __init__(self, gpio_num):
        self.gpio_num = gpio_num
        self.dutycycle = 0
        self.freq = 500

        self.init_pwm()
        logging.info(f"HW PWM Initialized")

    def __del__(self):
        self.pwmobj.hardware_PWM(self.gpio_num, 0, 0)
        self.pwmobj.stop()

    def init_pwm(self):
        self.pwmobj = pigpio.pi()
        self.pwmobj.set_mode(self.gpio_num, pigpio.OUTPUT)

    def set_pwm(self, pwm):
        #pwm is a float from 0-100
        logging.info(f"PWM set to {pwm}%%")
        pwm_int = int(pwm*10000)
        self.pwmobj.hardware_PWM(self.gpio_num, self.freq, pwm_int)

class button:
    #Button that sends a pulse for the duration of the press
    def __init__(self, gpio_num, callback_function):
        self.gpio_num = gpio_num
        self.callback_function = callback_function
        self.setup_gpio()
        logging.info(f"Button initialized on GPIO{gpio_num}")

    def setup_gpio(self):
        #Setup the GPIO direction
        gpio.setup(self.gpio_num, gpio.IN, pull_up_down=gpio.PUD_UP)
        gpio.add_event_detect(self.gpio_num, gpio.FALLING, bouncetime=2000, callback=self.callback_function)

class toggle_button:
    #Button that changes the state from 0->1 or 1->0 on each press (so we need to detect an event for both)
    def __init__(self, gpio_num, callback_function):
        self.gpio_num = gpio_num
        self.callback_function = callback_function
        self.setup_gpio()
        logging.info(f"Button initialized on GPIO{gpio_num}")

    def setup_gpio(self):
        #Setup the GPIO direction
        gpio.setup(self.gpio_num, gpio.IN, pull_up_down=gpio.PUD_UP)
        gpio.add_event_detect(self.gpio_num, gpio.BOTH, bouncetime=2000, callback=self.callback_function)

class switch:
    def __init__(self, gpio_num):
        self.gpio_num = gpio_num
        self.setup_gpio()
        logging.info(f"Switch initialized on GPIO{gpio_num}")

    def setup_gpio(self):
        #Setup the GPIO direction
        gpio.setup(self.gpio_num, gpio.IN, pull_up_down=gpio.PUD_UP)

    def get_state(self):
        return gpio.input(self.gpio_num)

class keypad:
    #This keypad function is meant to be called every 0.1 seconds as the other keypad function wasn't working properly
    #Still not sure why the other one doesn't work well tbh
    def __init__(self, pin_dict, callback_function):
        self.pin_dict = pin_dict
        self.callback_function = callback_function
        self.keypad_queue = Queue()
        self.setup_gpios()
        self.stop_flag = threading.Event()
        logging.info(f"Keypad initialized successfully")

        self._start_thread()

    def _start_thread(self):
        #Initialize the keypad_loop thread
        self.keypad_thread = threading.Thread(target=self._keypad_loop)
        self.keypad_thread.start()

    def setup_gpios(self):
        gpio.setup(self.pin_dict['row1'], gpio.OUT)
        gpio.setup(self.pin_dict['row2'], gpio.OUT)
        gpio.setup(self.pin_dict['row3'], gpio.OUT)
        gpio.setup(self.pin_dict['row4'], gpio.OUT)
        gpio.setup(self.pin_dict['col1'], gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.pin_dict['col2'], gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(self.pin_dict['col3'], gpio.IN, pull_up_down=gpio.PUD_DOWN)

    def _check_line(self, row, characters):
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

    def _keypad_loop(self):
        while(True):
            self._check_line(self.pin_dict['row1'], ["1","2","3"])
            self._check_line(self.pin_dict['row2'], ["4","5","6"])
            self._check_line(self.pin_dict['row3'], ["7","8","9"])
            self._check_line(self.pin_dict['row4'], ["star","0","pound"])
            time.sleep(0.05)

    def stop_thread(self):
        self.stop_flag.set()
        self.keypad_thread.join()

class keypad2:
    def __init__(self, pin_dict, callback_function):
        self.pin_dict = pin_dict
        self.callback_function = callback_function
        self.keypad_queue = Queue()
        self.setup_gpios()
        logging.info(f"Keypad initialized successfully")

    def setup_gpios(self):
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
        gpio.add_event_detect(self.pin_dict['col1'], gpio.RISING, bouncetime=200, callback=self.keypad_column_func)
        gpio.add_event_detect(self.pin_dict['col2'], gpio.RISING, bouncetime=200, callback=self.keypad_column_func)
        gpio.add_event_detect(self.pin_dict['col3'], gpio.RISING, bouncetime=200, callback=self.keypad_column_func)
        logging.info("Added button event interrupts for keypad")

    def reset_row_gpios(self):
        #Turn on the GPIOs
        gpio.output(self.pin_dict['row1'], gpio.HIGH)
        gpio.output(self.pin_dict['row2'], gpio.HIGH)
        gpio.output(self.pin_dict['row3'], gpio.HIGH)
        gpio.output(self.pin_dict['row4'], gpio.HIGH)
        logging.debug("Turned all the row gpio outputs back on")

    def keypad_column_func(self, gpionum):
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
        for key in self.pin_dict:
            if self.pin_dict[key] == gpionum:
                return key

if __name__ == "__main__":
    smart_bed()
