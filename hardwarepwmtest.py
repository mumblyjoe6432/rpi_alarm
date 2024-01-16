#!/usr/bin/env python3
#####################################################################################
# Filename    : LogicAnalyzer_HardwarePWM.py
# Description : Logic_Analyzer_With_Hardware_PWM
# Author      : Bob Fryer / Digital Shack
# modification: 22 Feb 2020
#####################################################################################
#####################################################################################
# Import the required Python Libraries
#####################################################################################
import pigpio                                   # import the pigpio library
import time                                     # Utilise the python time library
#####################################################################################
# Define the Variables Needed
#####################################################################################
pigpio_pin = 18         # define the GPIO Pin for PWM - pigpio only uses BCM numbers
RPI_DutyCycle = 100      # define the Duty Cycle in percentage  (50%)
RPI_Freq = 500          # define the frequency in Hz (500Hz)
RPI_LEDTime = 180       # define the time you want the LED to stay lit for
#####################################################################################
# Initialisation
#####################################################################################
pwmobj=pigpio.pi()                              # Define pwmobj as pigpio.pi()
pwmobj.set_mode(pigpio_pin, pigpio.OUTPUT)      # Set GPIO pin as output
#####################################################################################
# Define our LOOP Function
#####################################################################################
def light():
    pwmobj.hardware_PWM(pigpio_pin, RPI_Freq, RPI_DutyCycle * 10000) # Call PWM Func
    time.sleep(RPI_LEDTime)                                          # Stay lit
#####################################################################################
# Define our DESTROY Function
#####################################################################################
def destroy():
    pwmobj.hardware_PWM(pigpio_pin, 0, 0)               # turn off the LED/PWM
    pwmobj.stop()                                       # release pigpio resources
#####################################################################################
# Finally the code for the MAIN program
#####################################################################################
if __name__ == '__main__':                              # Program entry point
    print ('LED Duty Cycle of ', RPI_DutyCycle)         # Print duty cycle
    try:
        light()                                         # Call light function
    except KeyboardInterrupt:                           # Watches for Ctrl-C
        destroy()                                       # Call destroy function
    finally:
        destroy()                                       # Call destroy function