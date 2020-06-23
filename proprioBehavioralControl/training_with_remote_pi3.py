'''
Test SM
========
This is a test platform for using the state machine controller. Feel free to
change anything in this document and test it out.
'''

import os
from MonkeyGames.Effectors.Controllers.state_machine import State_Machine
from MonkeyGames.arbiter import Arbiter
from MonkeyGames.Effectors.Endpoints.rpi_gpio import GPIO_Input, GPIO_Output
from MonkeyGames.Effectors.Endpoints.file_printer import File_Printer
from MonkeyGames.Effectors.Processors.event_timestamper import Event_Timestamper

import RPi.GPIO as GPIO
import pdb, time, pygame, argparse

from game_states import *
import interfaces as ifaces
from helperFunctions import serial_ports

parser = argparse.ArgumentParser()
parser.add_argument('--enableSound', default = 'True')
parser.add_argument('--playWelcomeTone', default = 'True')
parser.add_argument('--playWhiteNoise', default = 'False')
parser.add_argument('--logLocally', default = 'False')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.01')

args = parser.parse_args()

# Power indicator
GPIO.setup(5, GPIO.OUT) ## Setup GPIO Pin 5 to OUT
GPIO.output(5,True) ## Turn on GPIO pin 5

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

# Setup IO Pins
butPin = GPIO_Input(pins = [4, 17], labels = ['red', 'green'],
    triggers = [GPIO.FALLING, GPIO.FALLING],
    levels = [GPIO.LOW, GPIO.LOW], bouncetime = 200)
timestamper = Event_Timestamper()

juicePin = GPIO_Output(pins=[13,6,26,25], labels=['leftLED', 'rightLED', 'bothLED', 'Reward'],
    levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH, GPIO.HIGH],
    instructions=['flip', 'flip', 'flip', ('pulse', .5)])

arbiter = Arbiter()
# Dummy state machine
SM = State_Machine()

# Add attributes to the state machine

# Add a mode to the state machine
SM.add_mode('sink', (['main_thread'], SM.inbox))
SM.add_mode('source', (['distributor'], True))

SM.speaker = speaker
SM.motor = motor
SM.inputPin = butPin

SM.enableLog = True
SM.firstVisit = True
SM.remoteOverride = None

# connect reward
arbiter.connect([(SM, 'source', True), juicePin])

# juicer override
def triggerJuice():
    speaker.tone_player('Good')()
    SM.outbox.put('Reward')

def exitGracefully():
    welcomeChime.play()

    if logToWeb:
        subprocess.check_output('sudo mount -a', shell = True)
        src = logFileName
        dst = serverFolder + '/' + SM.logFileName.split('/')[-1]

        shutil.move(src,dst)

        scriptPath = '/home/pi/research/Data-Analysis/evaluatePerformance.py'
        subprocess.check_output('python3 ' + scriptPath + ' --file '  + '\"' +
            logFileName.split('/')[-1] + '\"' + ' --folder \"' +
            serverFolder + '\"', shell=True)

    print('Ending Execution of training_with_remote.py')

try:
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
        serverFolder = '/media/browndfs/ENG_Neuromotion_Shared/group/Proprioprosthetics/Training/Flywheel Logs/Murdoc'
        values = [
            [sessionTime, 'Remote Control Session', '', '',
                'Log_Murdoc_' + sessionTime + '.txt', '', '', 'Murdoc_' + sessionTime]
            ]

        spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
        logEntryLocation = update_training_log(spreadsheetID, values)

        print(logEntryLocation)

    # separately log all button presses
    
    arbiter.connect([butPin, timestamper, thisLog])
    SM.add_state(do_nothing(['do_nothing'], SM, 'do_nothing', logFile = thisLog))
    SM.set_init('do_nothing')
    arbiter.run(SM)


    remoteControlMap = {
        "right" : motor.forward,
        "left" :  motor.backward,
        "enter" : motor.go_home,
        "a" : speaker.tone_player('Go'),
        "b" : speaker.tone_player('Good'),
        "c" : speaker.tone_player('Bad'),
        "0" : triggerJuice
    }

    remoteListener = ifaces.sparkfunRemoteInterface(
        mapping = remoteControlMap,
        default = lambda: None,
        confPath = wavePath + "/confAdafruit",
        remoteProgram = 'training')
    remoteListener.run()
    exitGracefully()
except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
    exitGracefully()
