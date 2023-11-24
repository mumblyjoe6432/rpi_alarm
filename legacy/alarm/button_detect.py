import RPi.GPIO as gpio
import time
import subprocess
import os
import signal
import random

#This loop will check for a button press every 50ms.  This delay also
#works as a button debouncer.  If the button is pressed, it will call
#the buttonpress function below.

def mainloop():
  inpin = 18

  gpio.cleanup()
  gpio.setmode(gpio.BCM)
  gpio.setup(inpin, gpio.IN)

  input_value = gpio.input(inpin)
  first = True
  while(True):
    time.sleep(.05)
    input_value = gpio.input(inpin)
    if input_value == True:
      if not first:
        buttonpress(inpin)
      time.sleep(.05)
      while(True):
        time.sleep(.05)
        input_value = gpio.input(inpin)
        if input_value == False:
          buttonpress(inpin)
          time.sleep(.05)
          break
    else:
        first = False

#buttonpress function
#Check if music is playing
#    Turn it off
#Check if alarm script is on
#    Turn it off
#Turn off the LEDs
#
#If neither the alarm script or music was playing, turn on sexy
#mode

def buttonpress(inpin):
#  alarm_script_pid = return_pid("alarm_script")
#
#  for pid in alarm_script_pid:
#    try:
#      os.kill(int(pid), signal.SIGTERM)
#      time.sleep(1)
#    except:
#      pass
#    gpio.cleanup()
#    gpio.setmode(gpio.BCM)
#    gpio.setup(4,gpio.OUT)
#    gpio.output(4,gpio.HIGH)
#    gpio.setup(inpin,gpio.IN)

  music_pid = return_pid("mpg123")
#  music_pid = return_pid("mplayer")
  
  for pid in music_pid:
    try:
      os.kill(int(pid), signal.SIGTERM)
      time.sleep(1)
    except:
      pass

#  if len(alarm_script_pid) == 0 and len(music_pid) == 0:
  if len(music_pid) == 0:
    rootdir = "/home/pi/music"
    song_file_list = os.listdir(rootdir)
    start_songs = os.listdir(rootdir+'/start')
    song_list = []
    for song in song_file_list:
      song_list.append(rootdir+"/"+song)
    random.shuffle(song_list)
    start_song_list = []
    for song in start_songs:
      start_song_list.append(rootdir+'/start/'+song)
    random.shuffle(start_song_list)
    for song in start_song_list:
      song_list.insert(0,song)
    song_list.insert(0,'-q')
#    song_list.insert(0,'--loop -1')
    song_list.insert(0,'mpg123')
#    song_list.insert(0,'mplayer')
    print song_list
    proc1 = subprocess.Popen(song_list)

def return_pid(procname):
  ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
  processes = ps.split('\n')
  proc_list = []
  for item in processes:
    if procname in item:
      proc_list.append(item)

  kill_list = []
  if len(proc_list) > 0:
    for entry in proc_list:
      pl = entry.split(' ')
      for item in pl:
        if item == '':
          pl.remove(item)
      kill_list.append(pl[1])

  return kill_list

mainloop()
