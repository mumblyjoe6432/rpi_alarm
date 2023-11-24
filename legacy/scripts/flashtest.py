#!/bin/python
import RPi.GPIO as g
import time

g.setmode(g.BOARD)
g.setup(7,g.OUT)
x=float(0)
g.output(7,g.LOW)

while(x<1):
  g.output(7,g.HIGH)
  time.sleep(1)
  g.output(7,g.LOW)
  time.sleep(1)
  x+=.0001
