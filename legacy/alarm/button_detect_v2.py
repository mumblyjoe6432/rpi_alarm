import RPi.GPIO as gpio
import time
import subprocess
import os
import signal
import random

#One main function that is called when the button is pressed.  It detects whether the alarm is running or not, can call other functions accordingly.

button1 = 18

#Initializer for button 1
def button1_init():
  gpio.cleanup()
  gpio.setmode(gpio.BCM)
  gpio.setup(button1, gpio.IN)
  try:
    gpio.remove_event_detect(button1)
    print "successfully removed event"
  except:
    pass
  gpio.add_event_detect(button1, gpio.BOTH, callback=button1_press, bouncetime=1000)

#This is the main loop that does nothing while waiting for interrupts
def mainloop():
  button1_init()
  while(True):
    time.sleep(0.5)

#If music is running, kill music player
#elif alarm script is running, kill alarm script
#else start the music playlist
def button1_press(wherefrom = None):
  print "BUTTON PRESS!"
  music_pid = return_pid("mpg123")
  for pid in music_pid:
    try:
      os.kill(int(pid), signal.SIGTERM)
      time.sleep(1)
    except:
      pass

  if len(music_pid) != 0:
    print "Killed music"
    return -1

  light_pid = return_pid("/home/pi/clock/clock")
  for pid in light_pid:
    try:
      os.kill(int(pid), signal.SIGTERM)
    except:
      pass
  time.sleep(1)
  turn_off_lights()

  if len(light_pid) != 0:
    print "Killed lights"
    return -2

  #Will look at /home/pi/music/start, randomize that list, and queue
  #After that in the queue, will add everything in /home/pi/music
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
  song_list.insert(0,'mpg123')
  proc1 = subprocess.Popen(song_list)
  print "Played music"
  return -3

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

def turn_off_lights():
  try:
    gpio.remove_event_detect(button1)
    print "successfully removed event2"
  except:
    pass
  time.sleep(.001)
  gpio.cleanup()
  gpio.cleanup()
  gpio.setmode(gpio.BCM)
  gpio.setup(4, gpio.OUT)
  gpio.output(4, gpio.HIGH)
  gpio.cleanup()
  gpio.cleanup()
  button1_init()

mainloop()
