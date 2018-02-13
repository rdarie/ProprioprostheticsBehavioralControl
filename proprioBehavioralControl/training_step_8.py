#!/usr/bin/env python3
'''
Training Step 8
========
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

import argparse, os, os.path, shutil, subprocess

# Power indicator
GPIO.setup(5, GPIO.OUT) ## Setup GPIO Pin 24 to OUT
GPIO.output(5,True) ## Turn on GPIO pin 24

# What time is it?
sessionTime = time.strftime("%Y_%m_%d_%H_%M_%S")

parser = argparse.ArgumentParser()
parser.add_argument('--trialLength', default = '1')
parser.add_argument('--trialTimeout', default = '3')
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--playWelcomeTone', default = 'True')
parser.add_argument('--playWhiteNoise', default = 'True')
parser.add_argument('--logLocally', default = 'False')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.08')

args = parser.parse_args()

argTrialLength = args.trialLength
argTrialTimeout = args.trialTimeout
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
'Wait' : wavePath + "/wait_tone.wav"
}

playWelcomeTone = True if args.playWelcomeTone == 'True' else False
if playWelcomeTone:
    pygame.mixer.init()
    welcomeChime = pygame.mixer.Sound(wavePath + "/violin_C5.wav")
    welcomeChime.set_volume(2 * argVolume)
    welcomeChime.play()

playWhiteNoise = True if args.playWhiteNoise == 'True' else False
if playWhiteNoise:
    whiteNoise = pygame.mixer.Sound(wavePath + "/whitenoisegaussian.wav")
    whiteNoise.set_volume(argVolume)
    whiteNoise.play(-1)

motor = ifaces.motorInterface(debugging = True, velocity = 4.3, acceleration = 200, deceleration = 200, useEncoder = True)
speaker = ifaces.speakerInterface(soundPaths = soundPaths,
    volume = argVolume, debugging = True, enableSound = argEnableSound)

"""
State Machine
"""
# Setup IO Pins
butPin = GPIO_Input(pins = [4, 17], labels = ['red', 'green'],
    triggers = [GPIO.FALLING, GPIO.FALLING],
    levels = [GPIO.LOW, GPIO.LOW], bouncetime = 200)
timestamper = Event_Timestamper()

juicePin = GPIO_Output(pins=[16,6,25], labels=['redLED', 'greenLED', 'Reward'],
    levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH],
    instructions=['flip', 'flip', ('pulse', .5)])

# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

# Add attributes to the state machine
SM.startEnable = False
SM.nominalTrialLength = float(argTrialLength)
SM.wrongTimeout = 7
SM.trialLength = SM.nominalTrialLength
SM.nextEnableTime = 0

SM.remoteOverride = None

SM.buttonTimedOut = False
SM.trialTimeout = float(argTrialTimeout)
SM.nextButtonTimeout = 0

SM.speaker = speaker
SM.motor = motor
SM.inputPin = butPin

SM.juicePin = juicePin

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

# send button presses to the state machine inbox
SM.request_last_touch = arbiter.connect([(butPin, 'read_last', True), SM],
    ['polled'])

# set up event logging
logLocally = True if args.logLocally == 'True' else False
if logLocally:
    logFileName = wavePath + '/logs/Log_Murdoc_' + sessionTime + '.txt'
else:
    logFileName = wavePath + '/debugLog.txt'

SM.logFileName = logFileName
thisLog = File_Printer(filePath = logFileName, append = True)

SM.magnitudeQueue = []
SM.lastCategory = None
SM.lastDirection = None
SM.easyReward = .05
SM.hardReward = .3

#block structure
SM.smallBlocLength = 2
SM.bigBlocLength = 2
SM.smallTally = 1
SM.bigTally = 1

SM.blocsRemaining = SM.bigBlocLength
SM.initBlocType = {
    'category' : 'big',
    'direction' : 'forward'
    }

#set up web logging
logToWeb = True if args.logToWeb == 'True' else False
if logToWeb:
    SM.serverFolder = '/media/browndfs/ENG_Neuromotion_Shared/group/Proprioprosthetics/Training/Flywheel Logs/Murdoc'
    values = [
        [sessionTime, 'Button Pressing Step 8', '', '',
            'Log_Murdoc_' + sessionTime + '.txt', '', '', 'Murdoc_' + sessionTime,
            SM.trialLength, SM.trialTimeout, argVolume, SM.easyReward, SM.hardReward,
            SM.smallBlocLength, SM.bigBlocLength]
        ]

    spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
    logEntryLocation = update_training_log(spreadsheetID, values)

    print(logEntryLocation)

# connect state machine states
SM.add_state(strict_fixation(['turnPedalRandom_1',  'fixation'], SM, 'fixation',
    thisLog))
SM.add_state(turnPedalRandom(['turnPedalRandom_2'], SM, 'turnPedalRandom_1',
    logFile = thisLog))
SM.add_state(turnPedalRandom(['clear_input_queue'], SM, 'turnPedalRandom_2',
    logFile = thisLog))
SM.add_state(clear_input_queue(['chooseNextTrial'], SM, 'clear_input_queue',
    logFile = thisLog))
SM.add_state(chooseNextTrial(['easy', 'hard'], SM, 'chooseNextTrial',
    logFile = thisLog))

# if in this trial, both buttons will be seen as correct
SM.add_state(set_correct(['goHard'], SM, 'hard', logFile = thisLog))
SM.add_state(trial_start(['wait_for_correct_button_timed_uncued'], SM, 'goHard',
    logFile = thisLog))
SM.add_state(wait_for_correct_button_timed_uncued(['good', 'bad',
    'wait_for_correct_button_timed_uncued'], SM,
    'wait_for_correct_button_timed_uncued', logFile = thisLog))

#if in this trial, a button will be assigned based on the longer direction
SM.add_state(set_correct(['goEasy'], SM, 'easy', logFile = thisLog))
SM.add_state(trial_start(['wait_for_correct_button_timed'], SM, 'goEasy',
    logFile = thisLog))
SM.add_state(wait_for_correct_button_timed(['good', 'bad',
    'wait_for_correct_button_timed'], SM, 'wait_for_correct_button_timed',
        logFile = thisLog))

SM.add_state(good(['post_trial'], SM, 'good', logFile = thisLog))
SM.add_state(bad(['post_trial'], SM, 'bad', logFile = thisLog))
SM.add_state(post_trial(['clear_input_queue_2'], SM, 'post_trial',
    logFile = thisLog))
SM.add_state(clear_input_queue(['fixation'], SM, 'clear_input_queue_2',
    logFile = thisLog))
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
    if logToWeb:
        subprocess.check_output('sudo mount -a', shell = True)
        src = SM.logFileName
        dst = SM.serverFolder + '/' + SM.logFileName.split('/')[-1]

        shutil.move(src,dst)

        scriptPath = dataAnalysisPath + '/dataAnalysis/behavioral/evaluatePerformance.py'
        subprocess.check_output('python3 ' + scriptPath +
            ' --file '  + '\"' + SM.logFileName.split('/')[-1] + '\" ' +
            ' --folder \"' +  SM.serverFolder + '\" ' +
            '--outputFileName \"' + SM.logFileName.split('/')[-1].split('.')[0] + '\" ',
            shell=True)

    print('Ending Execution of Training_step_8.py')

    GPIO.output(5,False) ## Turn off GPIO pin 5
    GPIO.cleanup() # cleanup all GPIO
