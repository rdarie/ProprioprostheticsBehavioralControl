'''
Test SM
========
This is a test platform for using the state machine controller. Feel free to
change anything in this document and test it out.
'''
import sys, os
sys.path.append('/home/pi/research/project-thalamus/')
from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output
from MonkeyGames.Effectors.Endpoints.file_printer import File_Printer
from MonkeyGames.Effectors.Processors.event_timestamper import Event_Timestamper

import RPi.GPIO as GPIO
import pdb, time, pygame, argparse

from game_states import *
import interfaces as ifaces
from helperFunctions import serial_ports

parser = argparse.ArgumentParser()
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--logToWeb', default = 'True')
parser.add_argument('--volume', default = '0.01')

args = parser.parse_args()

argEnableSound = True if args.enableSound == 'True' else False
argVolume = float(args.volume)

global wavePath
gitPath = os.path.dirname(os.path.realpath(__file__))
with open(gitPath + '/' + '.waveLocation', 'r') as wf:
    wavePath = wf.read().replace('\n', '')

soundPaths = {
'Go' : "go_tone.wav",
'Good' : "good_tone.wav",
'Bad' : 'bad_tone.wav'
}

speaker = ifaces.speakerInterface(soundPaths = soundPaths,
    volume = argVolume, debugging = True, enableSound = argEnableSound)

motor = ifaces.motorInterface(debugging = True)

"""
State Machine
"""
# Setup IO Pins
butPin = GPIO_Input(pins = [4, 17], labels = ['red', 'blue'],
                    triggers = [GPIO.FALLING, GPIO.FALLING],
                    levels = [GPIO.LOW, GPIO.LOW], bouncetime = 500)

timestamper = Event_Timestamper()

juicePin = GPIO_Output(pins=[12,13,25], labels=['redLED', 'blueLED','Reward'],
levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH], instructions=[('pulse', 1), 'flip', 'flip'])

try:
    remoteControlMap = {
        "right" : motor.forward,
        "left" : motor.backward,
        "enter" : motor.go_home,
        "a" : speaker.tone_player('Go'),
        "b" : speaker.tone_player('Good'),
        "c" : speaker.tone_player('Bad'),
        "up" : motor.set_home,
        "quit" : motor.stop_all
    }

    remoteListener = ifaces.sparkfunRemoteInterface(mapping = remoteControlMap, default = motor.default)
    remoteListener.run()

except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
