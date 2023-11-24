import RPi.GPIO as gpio
import time
import subprocess
import os
import signal
import random

#This script will kill the button script process if it is running
def mainloop():
  button_script_pid = return_pid("button_detect")
  print button_script_pid
  for pid in button_script_pid:
    try:
      os.kill(int(pid), signal.SIGTERM)
      time.sleep(1)
    except:
      pass

  if len(button_script_pid) == 0:
    print "Gabe's button script was not running, and therefore was not killed"

def return_pid(procname):
  processes = []
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
