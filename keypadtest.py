import RPi.GPIO as GPIO
import time

R1 = 26
R2 = 19
R3 = 13
R4 = 6

C1 = 21
C2 = 20
C3 = 16
#C4 = 21 #Only 3 columns

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(R1, GPIO.OUT)
GPIO.setup(R2, GPIO.OUT)
GPIO.setup(R3, GPIO.OUT)
GPIO.setup(R4, GPIO.OUT)

GPIO.setup(C1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
#GPIO.setup(C4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) #only have 3 columns

def keypad_column_func(column):
    print(f'Column {column} was pressed')

time.sleep(1)
#The add_event_detect function just doesn't work well without some hardware debouncing
GPIO.add_event_detect(C1, GPIO.RISING, bouncetime=2000, callback=keypad_column_func)
GPIO.add_event_detect(C2, GPIO.RISING, bouncetime=2000, callback=keypad_column_func)
GPIO.add_event_detect(C3, GPIO.RISING, bouncetime=2000, callback=keypad_column_func)

def readLine(line, characters):
    GPIO.output(line, GPIO.HIGH)
    if(GPIO.input(C1) == 1):
        pass
        print(characters[0])
    if(GPIO.input(C2) == 1):
        pass
        print(characters[1])
    if(GPIO.input(C3) == 1):
        pass
        print(characters[2])
    # if(GPIO.input(C4) == 1): #Only have 3 columns
    #     print(characters[3])
    GPIO.output(line, GPIO.LOW)

try:
    while True:
        # readLine(R1, ["1","2","3","A"])
        # readLine(R2, ["4","5","6","B"])
        # readLine(R3, ["7","8","9","C"])
        # readLine(R4, ["*","0","#","D"])
        readLine(R1, ["1","2","3"])
        readLine(R2, ["4","5","6"])
        readLine(R3, ["7","8","9"])
        readLine(R4, ["*","0","#"])
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nApplication stopped!")