#!/usr/bin/env python3
'''
Training Step 4
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
sessionTime = time.strftime("%d_%m_%Y_%H_%M_%S")

parser = argparse.ArgumentParser()
parser.add_argument('--trialLength', default = '10')
parser.add_argument('--trialTimeout', default = '5')
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--playWelcomeTone', default = 'True')
parser.add_argument('--playWhiteNoise', default = 'True')
parser.add_argument('--logLocally', default = 'False')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.1')

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
'Bad' : wavePath + "/bad_tone.wav"
}

playWelcomeTone = True if args.playWelcomeTone == 'True' else False
if playWelcomeTone:
    pygame.mixer.init()
    welcomeChime = pygame.mixer.Sound(wavePath + "/violin_C5.wav")
    welcomeChime.set_volume(argVolume)
    welcomeChime.play()

playWhiteNoise = True if args.playWhiteNoise == 'True' else False
if playWhiteNoise:
    whiteNoise = pygame.mixer.Sound(wavePath + "/whitenoisegaussian.wav")
    whiteNoise.set_volume(argVolume/2)
    whiteNoise.play(-1)

motor = ifaces.motorInterface(debugging = True)
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

juicePin = GPIO_Output(pins=[6,16,25], labels=['redLED', 'blueLED', 'Reward'],
    levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH],
    instructions=['flip', 'flip', ('pulse', .5)])

# Build an arbiter and a state machine
arbiter = Arbiter()
SM = State_Machine()

# Add attributes to the state machine
SM.startEnable = False
SM.trialLength = float(argTrialLength)
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

#set up web logging
logToWeb = True if args.logToWeb == 'True' else False
if logToWeb:
    SM.serverFolder = '/media/browndfs/ENG_Neuromotion_Shared/group/Proprioprosthetics/Training/Flywheel Logs/Murdoc'
    values = [
        [sessionTime, 'Button Pressing Step 3', '', '',
            'Log_Murdoc_' + sessionTime + '.txt', '', '', 'Murdoc_' + sessionTime]
        ]

    spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
    logEntryLocation = update_training_log(spreadsheetID, values)

    print(logEntryLocation)

# connect state machine states
SM.add_state(strict_fixation(['turnPedalRandom_1',  'fixation'], SM, 'fixation', thisLog))
SM.add_state(turnPedalRandom(['turnPedalRandom_2'], SM, 'turnPedalRandom_1', logFile = thisLog))
SM.add_state(turnPedalRandom(['wait'], SM, 'turnPedalRandom_2', logFile = thisLog))
SM.add_state(do_nothing(['trial_start'], SM, 'wait', logFile = thisLog))
SM.add_state(trial_start(['clear_input_queue'], SM, 'trial_start', logFile = thisLog))
SM.add_state(clear_input_queue(['wait_for_any_button_timed'], SM, 'clear_input_queue', logFile = thisLog))
SM.add_state(wait_for_any_button_timed(['good', 'post_trial'], SM, 'wait_for_any_button_timed', logFile = thisLog))
SM.add_state(good(['post_trial'], SM, 'good', logFile = thisLog))
SM.add_state(post_trial(['clear_input_queue_2'], SM, 'post_trial', logFile = thisLog))
SM.add_state(clear_input_queue(['fixation'], SM, 'clear_input_queue_2', logFile = thisLog))
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
    "up" : triggerJuice,
    "quit" : overRideAdder(SM, 'end')
}

remoteListener = ifaces.sparkfunRemoteInterface(mapping = remoteControlMap,
    default = lambda: None)
remoteListener.run()

welcomeChime.play()

if logToWeb:
    subprocess.check_output('sudo mount -a', shell = True)
    src = SM.logFileName
    dst = SM.serverFolder + '/' + SM.logFileName.split('/')[-1]

    shutil.move(src,dst)

    scriptPath = dataAnalysisPath + '/dataAnalysis/behavioral/evaluatePerformance.py'
    subprocess.check_output('python3 ' + scriptPath + ' --file '  + '\"' +
        SM.logFileName.split('/')[-1] + '\"' + ' --folder \"' +
        SM.serverFolder + '\"', shell=True)

print('Ending Execution of Training_step_3.py')

GPIO.output(5,False) ## Turn off GPIO pin 5
GPIO.cleanup() # cleanup all GPIO
