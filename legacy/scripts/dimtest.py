#!/bin/python
import RPi.GPIO as g
import time

g.setmode(g.BOARD)
g.setup(7,g.OUT)
x=float(0)
while(x<1):
  g.output(7,g.HIGH)
  time.sleep(.001)
  g.output(7,g.LOW)
  time.sleep(.01)
  x+=.0001
