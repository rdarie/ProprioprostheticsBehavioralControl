#!/usr/bin/env python3
'''
Training Step 1
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
import pdb, time, pygame, traceback

from game_states import *
import interfaces as ifaces
from helperFunctions import *
import numpy as np

import argparse, os, os.path, shutil, subprocess, time

# Power indicator
GPIO.setup(5, GPIO.OUT) ## Setup GPIO Pin 5 to OUT
GPIO.output(5, True) ## Turn on GPIO pin 5


# What time is it?
sessionTime = time.strftime("%Y_%m_%d_%H_%M_%S")

parser = argparse.ArgumentParser()
parser.add_argument('--responseWindow', default = '2')
parser.add_argument('--fixationDuration', default = '.5')
parser.add_argument('--wrongTimeout', default = '.5')
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--playWelcomeTone', default = 'True')
parser.add_argument('--playWhiteNoise', default = 'False')
parser.add_argument('--logLocally', default = 'False')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.1')

args = parser.parse_args()

DEBUGGING = True
if DEBUGGING:
    args.volume = '0.1'
    args.playWhiteNoise = 'False'
    args.responseWindow = '5'
    args.logToWeb = 'False'

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
    'Go' : wavePath + "/go_tone.wav",
    'Good' : wavePath + "/good_tone.wav",
    'Bad' : wavePath + "/bad_tone.wav",
    'Wait' : wavePath + "/wait_tone.wav",
    'Divider' : wavePath + "/divider_tone.wav"
    }

speaker = ifaces.speakerInterface(soundPaths = soundPaths,
    volume = argVolume, debugging = DEBUGGING, enableSound = argEnableSound, maxtime=250)
    
playWelcomeTone = True if args.playWelcomeTone == 'True' else False
if playWelcomeTone:
    welcomeChime = pygame.mixer.Sound(wavePath + "/violin_C5.wav")
    welcomeChime.set_volume(2 * argVolume)
    welcomeChime.play()

playWhiteNoise = True if args.playWhiteNoise == 'True' else False
if playWhiteNoise:
    whiteNoise = pygame.mixer.Sound(wavePath + "/whitenoisegaussian.wav")
    whiteNoise.set_volume(argVolume)
    whiteNoise.play(-1)

# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

motor = ifaces.motorInterface(
    serialPortName = '/dev/ttyUSB0',debugging = DEBUGGING, velocity = 1.5,
    jogVelocity=1.5, jogAcceleration=10,
    acceleration = 10, deceleration = 10, useEncoder = True,
    dummy=True)

SM.motor = motor

dummyMotor = ifaces.motorInterface(
    serialPortName = '/dev/ttyUSB1',debugging = DEBUGGING, velocity = 1.5,
    jogVelocity=2, jogAcceleration=30,
    acceleration = 15, deceleration = 15, useEncoder = True,
    dummy=True)

SM.dummyMotor = dummyMotor

"""
State Machine
"""
# Setup IO Pins
butPin = GPIO_Input(
    # pins = [12, 16],
    pins = [16, 12],
    # pins = [4, 11],
    labels = ['left', 'right'],
    triggers = [GPIO.RISING, GPIO.RISING],
    levels = [GPIO.HIGH, GPIO.HIGH], bouncetime = 200)
timestamper = Event_Timestamper()

juicePin = GPIO_Output(
    # pins=[6, 13, 26, 25],
    pins=[13, 6, 26, 25],
    # pins=[16, 6, 12, 25],
    labels=['leftLED', 'rightLED', 'bothLED', 'Reward'],
    levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH, GPIO.HIGH],
    instructions=['flip', 'flip', 'flip', ('pulse', .5)])

# Add attributes to the state machine
SM.startEnable = False
SM.nominalFixationDur = float(args.fixationDuration)
SM.wrongTimeout = float(argWrongTimeout)
SM.fixationDur = SM.nominalFixationDur
SM.nextEnableTime = 0

SM.remoteOverride = None

SM.buttonTimedOut = False
SM.responseWindow = float(args.responseWindow)
SM.nextButtonTimeout = 0

SM.speaker = speaker
SM.inputPin = butPin

SM.juicePin = juicePin
SM.smartPedal = None
# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

# send button presses to the state machine inbox
SM.request_last_touch = arbiter.connect(
    [(butPin, 'read_last', True), SM],
    ['polled']
    )

# set up event logging
logLocally = True if args.logLocally == 'True' else False
if logLocally:
    logFileName = wavePath + '/logs/Log_Rupert_' + sessionTime + '.txt'
else:
    logFileName = wavePath + '/debugLog.txt'

SM.logFileName = logFileName
thisLog = File_Printer(filePath = logFileName, append = True)
# thisLog = None

SM.magnitudeQueue = []
SM.lastCategory = None
SM.lastDirection = None

SM.cuedRewardDur = 1
SM.uncuedRewardDur = 3
SM.cuedJackpotRewardDur = 3
SM.uncuedJackpotRewardDur = 3
SM.jackpot = True

#  advance motor to starting position

# motor.step_size = 135e2
# motor.backward()
# time.sleep(2)
# motor.set_home()

# Set up throw distances
nSteps  = 9 # must be odd so that there is an equal # of A > B and B < A trials
assert nSteps % 2 == 1
midStep = int((nSteps - 1) / 2)
#units of hundredth of a degree
SM.jackpotSets = [(4,3), (4,5)]
SM.movementMagnitudes = np.linspace(10,100,nSteps) * 1e2
SM.movementSets = {
    'small' : [(4,1),(4,2),(4,3)],
    'big' : [(4,7),(4,6),(4,5)]
    }
SM.leftTally = 1
SM.rightTally = 1
SM.correctButton = None

SM.stimMotorThreshold = [
    1,
    1,
    1,
    0] # mA, per program
# DEBUGGING # SM.motorThreshold = [0, 0, 0, 0] # mA

SM.progNames = [
    'rostral',
    'caudal',
    'midline',
    'nostim'
    ]

SM.progLookup = {
    val: i for i, val in enumerate(SM.progNames)
    }
    
SM.progWeights = [
    3,
    3,
    3,
    1
    ]

SM.stimAmpMultipliers = [0.25, 0.5, 0.75]
# DEBUGGING!!!!
# SM.stimAmps = [1]
SM.stimFreqs = [2, 10, 100]
summit = ifaces.summitInterface(
    transmissionDelay=30e-3, dummy=False, verbose=True)
SM.summit = summit
SM.phantomMotor = True

#set up web logging
logToWeb = True if args.logToWeb == 'True' else False
if logToWeb:
    SM.serverFolder = '/media/browndfs/ENG_Neuromotion_Shared/group/Proprioprosthetics/Training/Flywheel Logs/Rupert'
    values = [
        [sessionTime, 'Button Pressing Step 2', '', '',
            'Log_Rupert_' + sessionTime + '.txt', '', '', 'Rupert_' + sessionTime,
            SM.nominalFixationDur, SM.responseWindow, argVolume, SM.cuedRewardDur, SM.uncuedRewardDur]
        ]

    spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
    logEntryLocation = update_training_log(spreadsheetID, values)

    print(logEntryLocation)

# connect state machine states
SM.add_state(strict_fixation(['turnPedalCompound',  'fixation'], SM, 'fixation',
    thisLog, printStatements = DEBUGGING, timePenalty=0.3))

SM.add_state(turnPedalCompoundWithStim(['chooseNextTrial'], SM, 'turnPedalCompound',
    logFile = thisLog, printStatements = True,
    smallProba=0.5, cWProba=0.5, angleJitter=5e2, waitAtPeak=0.1))
#
SM.add_state(chooseReportDifficulty(['waitEasy', 'waitHard'], SM, 'chooseNextTrial',
    logFile = None, probaBins = [0, .99, 1]))
#
SM.add_state(wait_for_correct_button_timed_uncued(['good', 'bad',
    'waitHard'], SM, 'waitHard', logFile = thisLog, printStatements = DEBUGGING))
#
SM.add_state(wait_for_correct_button_timed(['good', 'bad',
    'waitEasy'], SM, 'waitEasy', logFile = thisLog, printStatements = DEBUGGING))
#
SM.add_state(
    stochasticGood(
        ['post_trial'], SM, 'good',
        logFile=thisLog, printStatements=DEBUGGING, threshold=0.1))
#
SM.add_state(bad(['post_trial'], SM, 'bad', logFile = thisLog, printStatements = DEBUGGING))
#
SM.add_state(post_trial(['clear_input_queue_2'], SM, 'post_trial',
    logFile = thisLog, printStatements = DEBUGGING))
#
SM.add_state(clear_input_queue(['fixation'], SM, 'clear_input_queue_2',
    logFile = thisLog, printStatements = DEBUGGING))
#
SM.add_state(end([False], SM, 'end', logFile = thisLog))
#
SM.set_init('fixation')
time.sleep(1)
# connect reward
arbiter.connect([(SM, 'source', True), juicePin])

# juicer override
def triggerJuice():
    speaker.tone_player('Good')()
    SM.outbox.put('Reward')
    
# motor override
def toggleMotor():
    if SM.phantomMotor:
        SM.phantomMotor = False
    else:
        SM.phantomMotor = True

# separately log all button presses
arbiter.connect([butPin, timestamper, thisLog])
# also log all state machine events
arbiter.connect([(SM, 'source', True), timestamper, thisLog])

arbiter.run(SM)

remoteControlMap = {
    "right" : motor.forward,
    "left" :  motor.backward,
    "enter" : motor.go_home,
    "1" : speaker.tone_player('Go'),
    "2" : speaker.tone_player('Good'),
    "3" : speaker.tone_player('Bad'),
    "5": motor.toggle_jogging,
    "play" : triggerJuice,
    "enter": toggleMotor,
    "quit" : overRideAdder(SM, 'end')
}

remoteListener = ifaces.sparkfunRemoteInterface(
    mapping = remoteControlMap,
    default = lambda: None,
    confPath = wavePath + "/confAdafruit",
    remoteProgram = 'training')

welcomeChime.play()
try:
    remoteListener.run()

except Exception:
    traceback.print_exc()

finally:

    stimParams = {
        'Group' : 0,
        'Frequency' : 100,
        'DurationInMilliseconds' : 1000,
        'Amplitude' : [0,0,0,0],
        'PW' : [250,250,250,250],
        'ForceQuit' : True
        }

    summit.messageTrans(stimParams)
    # motor.stop_all()
    # dummyMotor.stop_all()
    # motor.step_size = 135e2
    # motor.forward()
    # motor.set_home()
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

    print('Ending Execution of Training_step_2.py')

    GPIO.output(5,False) ## Turn off GPIO pin 5
    GPIO.cleanup() # cleanup all GPIO
    thisLog.close()
