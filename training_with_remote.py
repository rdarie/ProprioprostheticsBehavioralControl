'''
Test SM
========
This is a test platform for using the state machine controller. Feel free to
change anything in this document and test it out.
'''

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
parser.add_argument('--playWhiteNoise', default = 'True')
parser.add_argument('--logLocally', default = 'False')
parser.add_argument('--logToWeb', default = 'False')
parser.add_argument('--volume', default = '0.01')

args = parser.parse_args()

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

juicePin = GPIO_Output(pins=[6,16,25], labels=['redLED', 'blueLED', 'Reward'],
    levels = [GPIO.HIGH, GPIO.HIGH, GPIO.HIGH],
    instructions=['flip', 'flip', ('pulse', .5)])

def exitGracefully():
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
        SM.serverFolder = '/media/browndfs/ENG_Neuromotion_Shared/group/Proprioprosthetics/Training/Flywheel Logs/Murdoc'
        values = [
            [sessionTime, 'Remote Control Session', '', '',
                'Log_Murdoc_' + sessionTime + '.txt', '', '', 'Murdoc_' + sessionTime]
            ]

        spreadsheetID = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'
        logEntryLocation = update_training_log(spreadsheetID, values)

        print(logEntryLocation)

    # separately log all button presses
    arbiter.connect([butPin, timestamper, thisLog])

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
    exitGracefully()
except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
    exitGracefully()
