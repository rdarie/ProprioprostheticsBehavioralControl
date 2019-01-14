#!/usr/bin/env python3
'''
Training Step 12
The "Go" tone goes off.
Buttons light up.

Within trialTimeout seconds, press any button.
Receive reward and "Good" tone on press, otherwise nothing happens.

Go to fixation.
Wait TrialLength seconds. During this time, if buttons are pressed,
the "Bad" tone is played, the script pauses for two seconds and the Wait
is increased by 2 seconds.

Go back to start.
'''

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

# Power indicator
GPIO.setup(5, GPIO.OUT) ## Setup GPIO Pin 5 to OUT
GPIO.output(5,True) ## Turn on GPIO pin 5


# What time is it?
sessionTime = time.strftime("%Y_%m_%d_%H_%M_%S")

parser = argparse.ArgumentParser()
parser.add_argument('--responseWindow', default = '1')
parser.add_argument('--interTrialInterval', default = '1')
parser.add_argument('--wrongTimeout', default = '1')
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--playWelcomeTone', default = 'True')
parser.add_argument('--playWhiteNoise', default = 'True')
parser.add_argument('--logLocally', default = 'False')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.08')

args = parser.parse_args()

argTrialLength = args.interTrialInterval
argTrialTimeout = args.responseWindow
argWrongTimeout = args.wrongTimeout
argEnableSound = True if args.enableSound == 'True' else False
argPlayWelcomeTone = args.playWelcomeTone
argVolume = float(args.volume)

global wavePath
curfilePath = os.path.abspath(__file__)
curDir = os.path.abspath(os.path.join(curfilePath,os.pardir)) # this will return current directory in which python file resides.
parentDir = os.path.abspath(os.path.join(curDir,os.pardir)) # this will return parent directory.

with open(parentDir + '/' + '.waveLocation', 'r') as wf:
    wavePath = wf.read().replace('\n', '')

with open(parentDir + '/' + '.dataAnalysisLocation', 'r') as f:
	dataAnalysisPath = f.read().replace('\n', '')

soundPaths = {
    'Go' : wavePath + "go_tone.wav",
    'Good' : wavePath + "good_tone.wav",
    'Bad' : wavePath + "bad_tone.wav",
    'Wait' : wavePath + "wait_tone.wav",
    'Divider' : wavePath + "divider_tone.wav"
    }

playWelcomeTone = True if args.playWelcomeTone == 'True' else False
if playWelcomeTone:
    pygame.mixer.init()
    welcomeChime = pygame.mixer.Sound(wavePath + "violin_C5.wav")
    welcomeChime.set_volume(2 * argVolume)
    welcomeChime.play()

playWhiteNoise = True if args.playWhiteNoise == 'True' else False
if playWhiteNoise:
    whiteNoise = pygame.mixer.Sound(wavePath + "whitenoisegaussian.wav")
    whiteNoise.set_volume(argVolume)
    whiteNoise.play(-1)


# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

motor = ifaces.motorInterface(serialPortName = '/dev/ttyUSB0',debugging = False, velocity = 2,
    acceleration = 250, deceleration = 250, useEncoder = True)

SM.motor = motor

"""
dummyMotor = ifaces.motorInterface(serialPortName = '/dev/ttyUSB1',debugging = True, velocity = 3,
    acceleration = 250, deceleration = 250, useEncoder = True)
"""
SM.dummyMotor = False

speaker = ifaces.speakerInterface(soundPaths = soundPaths,
    volume = argVolume, debugging = False, enableSound = argEnableSound)

"""
State Machine
"""
# Setup IO Pins
butPin = GPIO_Input(pins = [4, 17], labels = ['left', 'right'],
    triggers = [GPIO.FALLING, GPIO.FALLING],
    levels = [GPIO.HIGH, GPIO.HIGH], bouncetime = 200)
timestamper = Event_Timestamper()

juicePin = GPIO_Output(pins=[16,6,12,25], labels=['leftLED', 'rightLED', 'bothLED', 'Reward'],
    levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH, GPIO.HIGH],
    instructions=['flip', 'flip', 'flip', ('pulse', .5)])

# initialize outputs to movementOff
#GPIO.output(6,False)
#GPIO.output(16,False)
#GPIO.output(12,False)

# Add attributes to the state machine
SM.startEnable = False
SM.nominalTrialLength = float(argTrialLength)
SM.wrongTimeout = float(argWrongTimeout)
SM.trialLength = SM.nominalTrialLength
SM.nextEnableTime = 0

SM.remoteOverride = None

SM.buttonTimedOut = False
SM.trialTimeout = float(argTrialTimeout)
SM.nextButtonTimeout = 0

SM.speaker = speaker
SM.inputPin = butPin

SM.juicePin = juicePin
SM.smartPedal = None
# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

# send button presses to the state machine inbox
SM.request_last_touch = arbiter.connect([(butPin, 'read_last', True), SM],
    ['polled'])

# set up event logging
logLocally = True if args.logLocally == 'True' else False
if logLocally:
    logFileName = wavePath + 'logs/Log_Murdoc_' + sessionTime + '.txt'
else:
    logFileName = wavePath + 'debugLog.txt'

SM.logFileName = logFileName
thisLog = File_Printer(filePath = logFileName, append = True)

SM.magnitudeQueue = []
SM.lastCategory = None
SM.lastDirection = None

SM.easyReward = 1
SM.hardReward = 2
SM.jackpotReward = 3
SM.jackpot = True

# advance motor to starting position
motor.step_size = 135e2
motor.backward()
time.sleep(2)
motor.set_home()
# Set up throw distances
# import numpy as np
nSteps  = 9 # must be odd so that there is an equal # of A > B and B < A trials
assert nSteps % 2 == 1
midStep = int((nSteps - 1) / 2)

#units of hundredth of a degree
magnitudes = np.linspace(30,250,nSteps) * 1e2
sets = {
    'small' : [(4,0),(4,1),(4,0),(4,1),(4,4)],
    'big' : [(4,7),(4,6),(4,7),(4,6),(4,4)]
    }
SM.jackpotSets = [(4,4)]
SM.magnitudes = magnitudes
SM.sets = sets

#block structure
SM.smallBlocLength = 1
SM.bigBlocLength = 1
SM.smallTally = 1
SM.bigTally = 1

SM.blocsRemaining = SM.bigBlocLength

motorThreshold = 1 # mA
SM.stimAmps = [0.25, 0.5, 0.75]
SM.stimFreqs = [25, 50, 100]
summit = ifaces.summitInterface(transmissionDelay =70e-3)
SM.summit = summit
SM.initBlocType = {
    'category' : 'big',
    'direction' : 'forward'
    }
SM.correctButton = 'left'
#set up web logging
logToWeb = True if args.logToWeb == 'True' else False
if logToWeb:
    SM.serverFolder = '/media/browndfs/Proprioprosthetics/Training/Flywheel Logs/Murdoc'
    values = [
        [sessionTime, 'Button Pressing Step 13', '', '',
            'Log_Murdoc_' + sessionTime + '.txt', '', '', 'Murdoc_' + sessionTime,
            SM.trialLength, SM.trialTimeout, argVolume, SM.easyReward, SM.hardReward,
            SM.smallBlocLength, SM.bigBlocLength]
        ]

    spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
    logEntryLocation = update_training_log(spreadsheetID, values)

    print(logEntryLocation)

debugging = True
# connect state machine states
SM.add_state(strict_fixation(['turnPedalCompound',  'fixation'], SM, 'fixation',
    thisLog, printStatements = debugging))
SM.add_state(turnPedalCompoundWithStim(['chooseNextTrial'], SM, 'turnPedalCompound',
    logFile = thisLog, printStatements = debugging))
SM.add_state(chooseNextTrial(['waitEasy', 'waitHard'], SM, 'chooseNextTrial',
    logFile = None))

SM.add_state(wait_for_correct_button_timed_uncued(['good', 'bad',
    'waitHard'], SM, 'waitHard', logFile = thisLog, printStatements = debugging))
SM.add_state(wait_for_correct_button_timed(['good', 'bad',
    'waitEasy'], SM, 'waitEasy', logFile = thisLog, printStatements = debugging))

SM.add_state(variableGood(['post_trial'], SM, 'good', logFile = thisLog, printStatements = debugging))
SM.add_state(bad(['post_trial'], SM, 'bad', logFile = thisLog, printStatements = debugging))
SM.add_state(post_trial(['clear_input_queue_2'], SM, 'post_trial',
    logFile = thisLog, printStatements = debugging))
SM.add_state(clear_input_queue(['fixation'], SM, 'clear_input_queue_2',
    logFile = thisLog, printStatements = debugging))
SM.add_state(end([False], SM, 'end', logFile = thisLog))

SM.set_init('fixation')

# connect reward
arbiter.connect([(SM, 'source', True), juicePin])

# juicer override
def triggerJuice():
    speaker.tone_player('Good')()
    SM.outbox.put('Reward')

# separately log all button presses
arbiter.connect([butPin, timestamper, thisLog])
# also log all state machine events
arbiter.connect([(SM, 'source', True), timestamper, thisLog])

arbiter.run(SM)

remoteControlMap = {
    "right" : motor.forward,
    "left" :  motor.backward,
    "enter" : motor.go_home,
    "a" : speaker.tone_player('Go'),
    "b" : speaker.tone_player('Good'),
    "c" : speaker.tone_player('Bad'),
    "prev" : triggerJuice,
    "quit" : overRideAdder(SM, 'end')
}

remoteListener = ifaces.sparkfunRemoteInterface(mapping = remoteControlMap,
    default = lambda: None)

welcomeChime.play()
try:
    remoteListener.run()

except:
    pass

finally:

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

    motor.step_size = 135e2
    motor.forward()
    motor.set_home()
    if logToWeb:
        # this is the path to the the source file
        src = SM.logFileName
        # this is the path to the the destiantion file
        dst = SM.serverFolder + '/' + SM.logFileName.split('/')[-1]
        # move from source to destiantion
        shutil.move(src,dst)

        scriptPath = dataAnalysisPath + '/dataAnalysis/behavioral/evaluatePerformance2.py'
        subprocess.check_output('python3 ' + scriptPath +
            ' --file '  + '\"' + SM.logFileName.split('/')[-1] + '\" ' +
            ' --folder \"' +  SM.serverFolder + '\" ' +
            '--outputFileName \"' + SM.logFileName.split('/')[-1].split('.')[0] + '\" ',
            shell=True)

    print('Ending Execution of Training_step_13.py')

    GPIO.output(5,False) ## Turn off GPIO pin 5
    GPIO.cleanup() # cleanup all GPIO
    thisLog.close()
