import os
import subprocess
device = "gabenexus"
result = os.system("ping -c 30 " + device)
print "\n\nResult = ",result
if result == 0:
  command = ["touch", "/home/pi/alarm/phoneishere.record"]
  subprocess.Popen(command)
