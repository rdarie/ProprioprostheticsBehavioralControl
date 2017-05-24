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
import time, lirc, serial, pdb, random, sys

from raspPiInterface import raspPiInterface as RPI
from helperFunctions import serial_ports

availablePorts = serial_ports()

try:
    ser = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )
except:
    ser = serial.Serial(
        port=availablePorts[-1],
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )

ri = RPI(ser, goWavePath = "go_tone.wav",
    goodWavePath = "good_tone.wav",
    badWavePath = 'bad_tone.wav', debugging = True)
"""
State Machine
"""

# Setup IO Pins
butPin = GPIO_Input(pins = [17, 4], labels = ['red', 'blue'],
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

def fixation(self, cargo=None):
    sys.stdout.write("At fixation...\r")
    sys.stdout.flush()
    if SM.startEnable:
        return 'turnPedal'
    else:
        return 'fixation'

def turnPedal(self, cargo=None):
    pass

def set_correct(self, cargo = None):
    SM.correctButton = 'red' if random.randint(0,1) == 0 else 'blue'
    print('  ')
    print('Correct button set to: %s' % SM.correctButton)
    time.sleep(30)
    return 'wait_for_button'

def wait_for_button(self, cargo=None):
    print('Waiting for button')
    ri.play_go()
    # Read from inbox
    event_label = self.request_next_touch()

    print("%s button pressed!" % event_label[0])
    nextFun = 'good' if self.correctButton == event_label[0] else 'bad'
    return nextFun

def good(self, cargo=None):
    print('Good job!')
    ri.play_good()
    return 'set_correct'

def bad(self, cargo=None):
    print('Wrong! Try again!')
    ri.play_bad()
    return 'set_correct'

def end(self, cargo=None):
    print('Ending now')
    return False

SM.add_state(set_correct)
SM.add_state(wait_for_button)
SM.add_state(good)
SM.add_state(bad)
SM.add_state(end)
SM.set_init('set_correct')

arbiter.run(SM)

if __name__ == '__main__':
    try:
        interpret_command = {
            "right" : ri.forward,
            "left" : ri.backward,
            "enter" : ri.go_home,
            "a" : ri.play_go,
            "b" : ri.play_good,
            "c" : ri.play_bad,
            "up" : ri.set_home,
            "quit" : ri.stop_all
        }

        interpret_command = defaultdict(lambda: ri.default, interpret_command)

        #configure and initialize IR remote communication
        blocking = False

        code = "start"

        if(lirc.init("training", "conf", blocking = blocking)):

            while(code != "quit"):
                # Read next code
                ir_message = lirc.nextcode()
                #print("We've got mail!")

                # Loop as long as there are more on the queue
                # (dont want to wait a second if the user pressed many buttons...)
                while(ir_message):
                    # Run through commands
                    for (code) in ir_message:
                        #pdb.set_trace()
                        #run the function returned by interpret_command
                        interpret_command[code]()
                        if code == "quit":
                            break
                    #pdb.set_trace()
                    ir_message = lirc.nextcode()

    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        GPIO.cleanup() # cleanup all GPIO
