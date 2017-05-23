'''
Test SM
========
This is a test platform for using the state machine controller. Feel free to
change anything in this document and test it out.
'''
from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output
import time
import RPi.GPIO as GPIO
import pdb
import random

# Setup IO Pins
butPin = GPIO_Input(pins = [22, 17], labels = ['red', 'blue'],
                    triggers = [GPIO.FALLING, GPIO.FALLING], levels = [GPIO.LOW, GPIO.LOW], bouncetime = 500)

juicePin = GPIO_Output(pins=[27], labels=['Reward'],
                        instructions=[('pulse', 0.5)])

ledPin = GPIO_Output(pins=[23, 24], labels=['red', 'blue'],
                        instructions=[('pulse', 1)])

# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

# Add attributes to the state machine
SM.correctButton = 'red'
SM.startEnable = False
SM.targetAngle = []
SM.timeout = []
SM.slackTime = []
SM.postIncorrectTime = []
SM.postRewardTime = []

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

# SM.request_next_touch = arbiter.connect([(butPin, 'read_next', True), SM],['polled'])
# arbiter.connect([(SM, 'source', True), juicePin])

def setup(self, cargo=None):
    print('Setting up now')
    return 'set_correct'

def set_correct(self, cargo = None):
    SM.correctButton = 'red' if random.randint(0,1) == 0 else 'blue'
    print('  ')
    print('Correct button set to: %s' % SM.correctButton)
    return 'wait_for_button'

def wait_for_button(self, cargo=None):
    print('Waiting for button')
    # Read from inbox
    event_label = self.request_next_touch()

    print("%s button pressed!" % event_label[0])
    nextFun = 'good' if self.correctButton == event_label[0] else 'bad'
    return nextFun

def good(self, cargo=None):
    print('Good job!')
    return 'set_correct'

def bad(self, cargo=None):
    print('Wrong! Try again!')
    return 'set_correct'

def end(self, cargo=None):
    print('Ending now')
    return False

SM.add_state(setup)
SM.add_state(set_correct)
SM.add_state(wait_for_button)
SM.add_state(good)
SM.add_state(bad)
SM.add_state(end)
SM.set_init('setup')

arbiter.run(SM)

if __name__ == __main__:
    try:
        while True:
            pass
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        GPIO.cleanup() # cleanup all GPIO
