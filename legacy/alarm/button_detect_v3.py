import RPi.GPIO as gpio
import time
import subprocess
import os
import signal
import random
import threading
import math

DEBUG = False

class pi_gpios:
  def __init__(self):
    #Useful global variables to change
    self.button1 = 18 #input for the smiley face button
    self.ALARM_NUMSTEPS = 15 #15
    self.ALARM_STEPTIME = 60 #60
    self.ALARM_GPIO = 4 #output for the sunrise lights
    self.deviceip = "192.168.1.10"  #IP of "Gabe's phone".  Must be a string.

    #Useful file locations
    self.cronfileloc = "/home/pi/alarm/startalarm.start" #cron creates this file to start the alarm
    self.killfileloc = "/home/pi/alarm/killalarm.kill" #create this file to kill the script
    self.phonefile = "/home/pi/alarm/checkphone.task" #create this to know when to check for gabe's phone
    self.logfile = "/home/pi/alarm/gabegpio.log" #log file location
    self.musicdir = "/home/pi/music" #where the script looks for music
    self.startmusicdir = "/home/pi/music/start" #where the script looks for the music start

    #Program variables
    self.alarm_active = False
    self.disable_alarm = False
    self.disable_alarm_lock = threading.Lock()
    self.logfile_lock = threading.Lock()
    self.phonetrack = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    #GPIO initialization
    gpio.cleanup()
    gpio.setmode(gpio.BCM)
    gpio.setup(self.button1, gpio.IN)
    gpio.add_event_detect(self.button1, gpio.BOTH, bouncetime=200, callback=self.fnbutton1)
    gpio.setup(self.ALARM_GPIO, gpio.OUT)
    gpio.output(self.ALARM_GPIO, gpio.LOW)

    #Starting the main loop
    if DEBUG:
      print "-I- Finished Init, entering interrupt loop"
    self.logfile_lock.acquire(True)
    self.logmsg("-I- Finished Initialization, entering normal operation.")
    self.logfile_lock.release()
    self.interruptloop()

  def interruptloop(self):
    while(1):
      time.sleep(1)

      #This sequence detects if the alarm sequence should be started
      try:
        f = open(self.cronfileloc,'r')
        self.logfile_lock.acquire(True)
        self.logmsg("-I- Started alarm sequence thread")
        self.logfile_lock.release()
        t1 = threading.Thread(target=self.alarm_sequence)
        t1.start()
        f.close()
        os.remove(self.cronfileloc)
      except:
        pass

      #This sequence detects if the ping phone sequence should be started
      try:
        f = open(self.phonefile,'r')
        t2 = threading.Thread(target=self.ping_phone)
        t2.start()
        f.close()
        os.remove(self.phonefile)
      except:
        pass

      #This sequence detects if we need to kill the program
      try:
        f = open(self.killfileloc,'r')
        self.logfile_lock.acquire(True)
        self.logmsg("-I- Received signal to kill the process.")
        self.logfile_lock.release()
        self.disable_alarm_lock.acquire(True)
        self.disable_alarm = True
        self.disable_alarm_lock.release()
        if DEBUG:
          print "Process killed"
        self.logfile_lock.acquire(True)
        self.logmsg("-I- Sent the kill signal to the alarm thread, if active.")
        self.logfile_lock.release()
        music_pid = self.return_pid("mpg123")
        if len(music_pid) != 0:
          for pid in music_pid:
            try:
              os.kill(int(pid), signal.SIGTERM)
              time.sleep(1)
            except:
              pass
        f.close()
        os.remove(self.killfileloc)
        self.logfile_lock.acquire(True)
        self.logmsg("-I- Process killed.")
        self.logfile_lock.release()
        return
      except:
        pass

  def fnbutton1(self,channel):
    self.logfile_lock.acquire(True)
    self.logmsg("-I- Button press detected on channel %s."%channel)
    self.logfile_lock.release()
    if DEBUG:
      print "Button Pressed!"
      print "Channel =", channel
    if self.alarm_active:
      self.disable_alarm_lock.acquire(True)
      self.disable_alarm = True
      self.disable_alarm_lock.release()
      self.logfile_lock.acquire(True)
      self.logmsg("-I- Alarm was found to be active, and has been killed.")
      self.logfile_lock.release()
      if DEBUG:
        print "Alarm will disable soon"
      return
    
    gpio.output(self.ALARM_GPIO, gpio.LOW)
    music_pid = self.return_pid("mpg123")
    if len(music_pid) != 0:
      for pid in music_pid:
        try:
          os.kill(int(pid), signal.SIGTERM)
          time.sleep(1)
        except:
          pass
      self.logfile_lock.acquire(True)
      self.logmsg("-I- Music player was found to be active, and has been killed.")
      self.logfile_lock.release()
      return

    self.start_music()

  def alarm_sequence(self):
    if DEBUG:
      print "Started the Alarm Sequence"
      print "ALARM_STEPTIME =", self.ALARM_STEPTIME
      print "ALARM_NUMSTEPS =", self.ALARM_NUMSTEPS
    hr=time.localtime()[3]
    count = self.phonetrack[hr]+self.phonetrack[hr-1]+self.phonetrack[hr-2]+self.phonetrack[hr-3]+self.phonetrack[hr-4]+self.phonetrack[hr-5]
    if count < 1:
      self.logfile_lock.acquire(True)
      self.logmsg("-I- Gabe's cell phone not found. Stopping alarm sequence. %s"%self.phonetrack)
      self.logfile_lock.release()
      return

    self.logfile_lock.acquire(True)
    self.logmsg("-I- Alarm sequence thread active. STEPTIME=%s, NUMSTEPS=%s."%(self.ALARM_STEPTIME, self.ALARM_NUMSTEPS))
    self.logfile_lock.release()
    self.alarm_active = True

    i = self.ALARM_NUMSTEPS
    while i > 0:
      pwm = float(math.log(i,self.ALARM_NUMSTEPS+1))
      offtime = pwm/1000
      ontime = (1-pwm)/1000

      pwm_cycle_start_time = time.time()
      if DEBUG:
         print "Started cycle %s, ontime=%s, offtime=%s pwm=%s"%(self.ALARM_NUMSTEPS-i, ontime, offtime, pwm)
      while (time.time() < pwm_cycle_start_time + self.ALARM_STEPTIME):
        gpio.output(self.ALARM_GPIO, gpio.LOW)
        time.sleep(offtime)
        self.disable_alarm_lock.acquire(True)
        if self.disable_alarm:
          if DEBUG:
            print "Stopping the alarm sequence"
          self.disable_alarm= False
          self.disable_alarm_lock.release()
          self.alarm_active = False
          gpio.output(self.ALARM_GPIO, gpio.LOW)
          return
        self.disable_alarm_lock.release()
        gpio.output(self.ALARM_GPIO, gpio.HIGH)
        time.sleep(ontime)
      i-=1

    self.logfile_lock.acquire(True)
    self.logmsg("-I- Alarm sequence finished. Starting OPB stream and exiting.")
    self.logfile_lock.release()
    opb_list = ["mpg123", "--loop", "-1", "-@", "http://www.opb.org/programs/streams/opb-radio.pls"]
    proc1 = subprocess.Popen(opb_list)
    self.alarm_active = False

  def ping_phone(self):
    result = os.system("ping -c 30 " + self.deviceip)
    hr = time.localtime()[3]
    if result == 0:
      self.phonetrack[hr] = 1
      self.logfile_lock.acquire(True)
      self.logmsg("-I- Gabe's phone WAS found on the network.")
      self.logfile_lock.release()
    else:
      self.phonetrack[hr] = 0
      self.logfile_lock.acquire(True)
      self.logmsg("-I- Gabe's phone WAS NOT found on the network.")
      self.logfile_lock.release()

  def start_music(self):
    self.logfile_lock.acquire(True)
    self.logmsg("-I- Starting the music player.")
    self.logfile_lock.release()
    #Will look at /home/pi/music/start, randomize that list, and queue
    #After that in the queue, will add everything in /home/pi/music
    song_file_list = os.listdir(self.musicdir)
    start_songs = os.listdir(self.startmusicdir)
    song_list = []
    for song in song_file_list:
      song_list.append(self.musicdir+"/"+song)
    random.shuffle(song_list)
    start_song_list = []
    for song in start_songs:
      start_song_list.append(self.startmusicdir+'/'+song)
    random.shuffle(start_song_list)
    for song in start_song_list:
      song_list.insert(0,song)
    song_list.insert(0,'-q')
    song_list.insert(0,'mpg123')
    proc1 = subprocess.Popen(song_list)

  def return_pid(self, procname):
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

  def logmsg(self, msg):
    temp = time.localtime()
    timestr = "[%02.f/%02.f/%02.f %02.f:%02.f:%02.f] "%(temp[1],temp[2],temp[0],temp[3],temp[4],temp[5])
    f=open(self.logfile, 'a')
    f.write(timestr+msg+'\n')
    f.close()

#GPIO initializer
if __name__ == "__main__":
  trash = pi_gpios()
