'''
Test SM
========
This is a test platform for using the state machine controller. Feel free to
change anything in this document and test it out.
'''
from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output

import RPi.GPIO as GPIO
import pdb

from game_states import *
import interfaces as ifaces
from helperFunctions import serial_ports

soundPaths = {
'Go' : "go_tone.wav",
'Good' : "good_tone.wav",
'Bad' : 'bad_tone.wav'
}

speaker = ifaces.speakerInterface(soundPaths = soundPaths,
    volume = 0.001, debugging = True, enableSound = False)
motor = ifaces.motorInterface(debugging = True)

"""
State Machine
"""
# Setup IO Pins
butPin = GPIO_Input(pins = [4, 17], labels = ['red', 'blue'],
                    triggers = [GPIO.FALLING, GPIO.FALLING], levels = [GPIO.LOW, GPIO.LOW], bouncetime = 500)

#juicePin = GPIO_Output(pins=[27], labels=['Reward'],
#                        instructions=[('pulse', 0.5)])

ledPin = GPIO_Output(pins=[5,6], labels=['red', 'blue'],
                        instructions=[('pulse', 1)])

# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

# Add attributes to the state machine
SM.correctButton = 'red'
SM.startEnable = False
SM.trialLength = 2
SM.nextEnableTime = 0
SM.speaker = speaker
SM.motor = motor
SM.inputPin = butPin
SM.targetAngle = []
SM.timeout = []
SM.slackTime = []
SM.postIncorrectTime = []
SM.postRewardTime = []

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

SM.request_last_touch = arbiter.connect([(butPin, 'read_last', True), SM],
    ['polled'])
# arbiter.connect([(SM, 'source', True), juicePin])

SM.add_state(fixation_constructor(nextState = ['set_correct',  'fixation']))
SM.add_state(set_correct_constructor(nextState = ['trial_start']))
SM.add_state(trial_start_constructor(nextState = ['clear_input_queue']))
SM.add_state(clear_input_queue_constructor(nextState = ['wait_for_correct_button']))
SM.add_state(wait_for_correct_button_constructor(nextState = ['good', 'bad']))
SM.add_state(good_constructor(nextState = ['post_trial']))
SM.add_state(bad_constructor(nextState = ['post_trial']))
SM.add_state(post_trial_constructor(nextState = ['fixation']))
SM.add_state(end_constructor())

SM.set_init('set_correct')

try:
    arbiter.run(SM)
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
