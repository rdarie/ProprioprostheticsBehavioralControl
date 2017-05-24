'''
Test SM
========
This is a test platform for using the state machine controller. Feel free to
change anything in this document and test it out.
'''
from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output
from collections import defaultdict
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
SM.trialLength = 10.
SM.nextEnableTime = 0
SM.speaker = speaker
SM.motor = motor
SM.targetAngle = []
SM.timeout = []
SM.slackTime = []
SM.postIncorrectTime = []
SM.postRewardTime = []

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

SM.request_next_touch = arbiter.connect([(butPin, 'read_next', True), SM],['polled'])
# arbiter.connect([(SM, 'source', True), juicePin])

SM.add_state(set_correct)
SM.add_state(turnPedal)
SM.add_state(fixation)
SM.add_state(wait_for_button)
SM.add_state(good)
SM.add_state(bad)
SM.add_state(post_trial)
SM.add_state(end)
SM.set_init('set_correct')

arbiter.run(SM)

if __name__ == '__main__':
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
