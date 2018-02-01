import pygame, pdb, lirc, serial, os, os.path
from helperFunctions import serial_ports

global wavePath

curfilePath = os.path.abspath(__file__)
curDir = os.path.abspath(os.path.join(curfilePath,os.pardir)) # this will return current directory in which python file resides.
parentDir = os.path.abspath(os.path.join(curDir,os.pardir)) # this will return parent directory.

with open(parentDir + '/' + '.waveLocation', 'r') as wf:
    wavePath = wf.read().replace('\n', '')

class speakerInterface(object):
    def __init__(self, soundPaths, volume = 1,
        debugging = False, enableSound = True):

        pygame.mixer.init()
        self.volume = volume
        self.enableSound = enableSound

        # audio, Pygame implementation
        self.sounds = {key : pygame.mixer.Sound(value)
            for key, value in soundPaths.items()}

        for key, value in self.sounds.items():
            value.set_volume(volume)

        self.debugging = debugging

    def play_tone(self, key):
        if self.enableSound:
            self.sounds[key].play()

        if self.debugging:
            print('Played the '+ key + ' tone')

    def tone_player(self, key):
    #returns a function that takes no arguments and plays the tone specified by key
        def tone_playerDummyMethod():
            self.play_tone(key)
        return tone_playerDummyMethod

class sparkfunRemoteInterface(object):
    def __init__(self, mapping, default):
        self.default = default
        self.mapping = mapping

    def run(self):
        #configure and initialize IR remote communication
        blocking = False
        code = "start"

        if(lirc.init("training", wavePath + "/confAdafruit", blocking = blocking)):

            while(code != "quit"):
                # Read next code
                ir_message = lirc.nextcode()

                # Loop as long as there are more on the queue
                while(ir_message):
                    # Run through commands
                    for code in ir_message:
                        #pdb.set_trace()
                        #run the function returned by interpret_command
                        funcToRun = self.mapping.get(code, self.default)
                        ir_message.remove(code)
                        funcToRun()
                        if code == "quit":
                            break
                        #TODO: make this not break the state machine execution
                    ir_message = lirc.nextcode()

class motorInterface(object):
    # Configure the serial port connection the the Si3540 motor driver
    def __init__(self, serialPortName = '/dev/ttyUSB0', debugging = False):
        try:
            ser = serial.Serial(
                port= serialPortName,
                baudrate = 9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
                )
        except:
            print('Unable to connect to ' + serialPortName)
            availablePorts = serial_ports()
            print('defaulting to: ' + availablePorts[-1])
            serialPortName = availablePorts[-1]

            ser = serial.Serial(
                port=availablePorts[-1],
                baudrate = 9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
                )

        self.current_position = 0
        self.step_size = 30e3
        self.serialPortName = serialPortName
        self.serial = ser

        self.current = 3.2
        serial_message = "CC" + str(self.current) + "\r"
        self.serial.write(serial_message.encode())
        self.idle_current = 3.2
        serial_message = "CI" + str(self.idle_current) + "\r"
        self.serial.write(serial_message.encode())

        self.velocity = 6 #move speed in rev/sec. Range is .025 - 50
        # note that the worm gearbox is 7.5:1 ratioed
        serial_message = "VE" + str(self.velocity) + "\r"
        self.serial.write(serial_message.encode())

        self.acceleration = 200 #move speed in rev/sec^2.
        serial_message = "AC" + str(self.acceleration) + "\r"
        self.serial.write(serial_message.encode())

        self.deceleration = 200 #move speed in rev/sec^2.
        serial_message = "DE" + str(self.deceleration) + "\r"
        self.serial.write(serial_message.encode())

        # Initialize motor

        self.debugging = debugging

    def set_home(self):
        self.current_position = 0
        if self.debugging:
            print("Home position was reset")

    def forward(self):
        if self.debugging:
            print("going clockwise")

        serial_message = "DI"+str(int(self.step_size))+"\r"

        self.serial.write(serial_message.encode())

        if self.debugging:
            print("sent message: " + serial_message)

        self.serial.write("FL\r".encode())

        self.current_position += self.step_size

        if self.debugging:
            print("Currently at %d steps" % self.current_position)

    def backward(self):
        if self.debugging:
            print("going counter-clockwise")

        serial_message = "DI"+str(-int(self.step_size))+"\r"

        self.serial.write(serial_message.encode())
        self.serial.write("FL\r".encode())

        self.current_position -= self.step_size

        if self.debugging:
            print("Currently at %d steps" % self.current_position)

    def shorten(self):
        self.step_size -= 100
        if self.debugging:
            print("Shortened step size to: %d steps" % self.step_size)

    def lengthen(self):
        self.step_size += 100
        if self.debugging:
            print("Lengthened step size to: %d steps" % self.step_size)

    def default(self):
        print("Default ")

    def go_home(self):
        if self.current_position != 0:
            hold_step_size = self.step_size
            self.step_size = abs(self.current_position)

            if self.debugging:
                print("Going home!")

            if self.current_position > 0:
                self.backward()
            else:
                self.forward()

            self.step_size = hold_step_size

    def stop_all(self):
        serial_message = "SK\r"
        self.serial.write(serial_message.encode())
        if self.debugging:
            print("Stopped all and exiting!")
