import time

# Import ZeroMQ package
import zmq
import json
import traceback
from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Processors.event_timestamper import Event_Timestamper
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output
from MonkeyGames.Effectors.Endpoints.file_printer import File_Printer

import RPi.GPIO as GPIO
import pdb, time, pygame

from game_states import *
import interfaces as ifaces
from helperFunctions import *
import numpy as np

import argparse, os, os.path, shutil, subprocess, time

motor = ifaces.motorInterface(serialPortName = '/dev/ttyUSB0',debugging = False, velocity = 2,
    acceleration = 250, deceleration = 250, useEncoder = True)
motor.step_size = 90e2
# Power indicator
GPIO.setup(25, GPIO.OUT) ## Setup GPIO Pin 25 to OUT

summit = ifaces.summitInterface(transmissionDelay =100e-3)
frequencies = [25, 50, 100]
try:
    for i in range(102):
        print('On trial {}'.format(i))
        amplitudes = [0,0,0,0]
        idx = i % 2
        amplitudes[idx] = 1
        frequency = frequencies[i % 3]

        summit.freqChange(frequency)
        time.sleep(0.5)

        GPIO.output(25,True) ## Turn on GPIO pin 25
        summit.stimOneMovement(amplitudes, .250, frequency)
        time.sleep(summit.transmissionDelay + 2/frequency)

        # advance motor
        motor.backward()
        time.sleep(1.5)

        # reset
        motor.forward()
        GPIO.output(25,False) ## Turn on GPIO pin 25
        time.sleep(1.5)
finally:
    GPIO.output(25,False) ## Turn on GPIO pin 25
    stimParams = {
        'Group' : 0,
        'Frequency' : 100,
        'DurationInMilliseconds' : 1000,
        'Amplitude' : [0,0,0,0],
        'PW' : [250,250,250,250],
        'ForceQuit' : True,
        'AddReverse' : False
        }
    summit.messageTrans(stimParams)
