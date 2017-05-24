'''
Training Step 1
========
The "Go" tone goes off.

Unlimited time, press any button.
Receive reward and "Good" tone.

Wait XX seconds. During this time, buttons are inactive,
but pressing them doesn't hurt.

Go back to start.
'''

from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output

import RPi.GPIO as GPIO
import pdb

from game_states import *
import interfaces as ifaces
from helperFunctions import serial_ports

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--trialLength', default = '10')
args = parser.parse_args()
argTrialLength = args.trialLength

soundPaths = {
'Go' : "go_tone.wav",
'Good' : "good_tone.wav"
}

speaker = ifaces.speakerInterface(soundPaths = soundPaths,
    volume = 0.001, debugging = True, enableSound = False)

"""
State Machine
"""
# Setup IO Pins
butPin = GPIO_Input(pins = [4, 17], labels = ['red', 'blue'],
                    triggers = [GPIO.FALLING, GPIO.FALLING], levels = [GPIO.LOW, GPIO.LOW], bouncetime = 500)

#juicePin = GPIO_Output(pins=[27], labels=['Reward'],
#                        instructions=[('pulse', 0.5)])

# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

# Add attributes to the state machine
SM.startEnable = False
SM.trialLength = float(argTrialLength)
SM.nextEnableTime = 0
SM.speaker = speaker
SM.inputPin = butPin

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

SM.request_last_touch = arbiter.connect([(butPin, 'read_last', True), SM],
    ['polled'])

SM.add_state(fixation_constructor(nextState = ['trial_start',  'fixation']))
SM.add_state(trial_start_constructor(nextState = ['clear_input_queue']))
SM.add_state(clear_input_queue_constructor(nextState = ['wait_for_any_button']))
SM.add_state(wait_for_any_button_constructor(nextState = ['good']))
SM.add_state(good_constructor(nextState = ['post_trial']))
SM.add_state(post_trial_constructor(nextState = ['fixation']))
SM.add_state(end_constructor())

SM.set_init('fixation')

try:
    arbiter.run(SM)
    remoteControlMap = {
        "right" : lambda: None,
        "left" : lambda: None,
        "enter" : lambda: None,
        "a" : speaker.tone_player('Go'),
        "b" : speaker.tone_player('Good'),
        "c" : speaker.tone_player('Bad'),
        "up" : lambda: None,
        "quit" : lambda: None
    }

    remoteListener = ifaces.sparkfunRemoteInterface(mapping = remoteControlMap, default = lambda: None)
    remoteListener.run()

except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
