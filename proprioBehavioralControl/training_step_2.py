#!/usr/bin/env python3
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
import sys
sys.path.append('/home/pi/research/project-thalamus/')
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

import argparse, os, shutil, subprocess

# Power indicator
GPIO.setup(5, GPIO.OUT) ## Setup GPIO Pin 24 to OUT
GPIO.output(5,True) ## Turn on GPIO pin 24

parser = argparse.ArgumentParser()
parser.add_argument('--trialLength', default = '3')
parser.add_argument('--trialTimeout', default = '7')
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--playWelcomeTone', default = 'True')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.01')

args = parser.parse_args()

argTrialLength = args.trialLength
argTrialTimeout = args.trialTimeout
argEnableSound = True if args.enableSound == 'True' else False
argPlayWelcomeTone = args.playWelcomeTone
argVolume = float(args.volume)

global wavePath
gitPath = os.path.dirname(os.path.realpath(__file__))
with open(gitPath + '/' + '.waveLocation', 'r') as wf:
    wavePath = wf.read().replace('\n', '')

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
butPin = GPIO_Input(pins = [4, 17], labels = ['red', 'blue'],
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
SM.inputPin = butPin

SM.juicePin = juicePin

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

SM.request_last_touch = arbiter.connect([(butPin, 'read_last', True), SM],
    ['polled'])

sessionTime = time.strftime("%d_%m_%Y_%H_%M_%S")
logFileName = wavePath + '/logs/Log_Murdoc_' + sessionTime + '.txt'
SM.logFileName = logFileName

logToWeb = True if args.logToWeb == 'True' else False

if logToWeb:
    SM.serverFolder = '/media/browndfs/ENG_Neuromotion_Shared/group/Proprioprosthetics/Training/Flywheel Logs/Murdoc'
    values = [
        [sessionTime, 'Button Pressing Step 2', '', '',
            'Log_Murdoc_' + sessionTime + '.txt', '', '', 'Murdoc_' + sessionTime]
        ]

    spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
    logEntryLocation = update_training_log(spreadsheetID, values)

    print(logEntryLocation)
thisLog = File_Printer(filePath = logFileName, append = True)

SM.add_state(fixation(['trial_start',  'fixation'], SM, 'fixation', thisLog))
SM.add_state(trial_start(['clear_input_queue'], SM, 'trial_start', logFile = thisLog))
SM.add_state(clear_input_queue(['wait_for_any_button_timed'], SM, 'clear_input_queue', logFile = thisLog))
SM.add_state(wait_for_any_button_timed(['good', 'post_trial'], SM, 'wait_for_any_button_timed', logFile = thisLog))
SM.add_state(good(['post_trial'], SM, 'good', logFile = thisLog))
SM.add_state(post_trial(['fixation'], SM, 'post_trial', logFile = thisLog))
SM.add_state(end([False], SM, 'end', logFile = thisLog))

SM.set_init('fixation')

arbiter.connect([(SM, 'source', True), juicePin])
#arbiter.connect([(SM, 'source', True), butLED])

def triggerJuice():
    speaker.tone_player('Good')()
    SM.outbox.put('Reward')

arbiter.connect([butPin, timestamper, thisLog])
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

    scriptPath = '/home/pi/research/Data-Analysis/evaluatePerformance.py'
    subprocess.check_output('python3 ' + scriptPath + ' --file '  + '\"' +
        SM.logFileName.split('/')[-1] + '\"' + ' --folder \"' +
        SM.serverFolder + '\"', shell=True)

print('Ending Execution of Training_step_2.py')

GPIO.output(5,False) ## Turn off GPIO pin 5
GPIO.cleanup() # cleanup all GPIO
