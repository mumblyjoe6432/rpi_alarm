#!/bin/python
import RPi.GPIO as g

g.cleanup()
g.setmode(g.BCM)
g.setup(4,g.OUT)
g.output(4,g.HIGH)
g.cleanup()
