#! /usr/bin/env python

import pylirc, serial, time, pdb, wiringpi, sys, glob
from collections import defaultdict

class remote_interface(object):
    def __init__(self, serial, debugging = False):
        self.current_position = 0
        self.step_size = 10000
        self.serial = serial

        self.debugging = debugging

        self.tonePin = 2
        wiringpi.wiringPiSetupGpio()
        wiringpi.pinMode(self.tonePin,1)
        wiringpi.softToneCreate(self.tonePin) # Setup PWM using Pin, Initial Value and Range parameters

    def set_home(self):
        self.current_position = 0
        if self.debugging:
            print("Reset home position")

    def forward(self):
        if self.debugging:
            print("going clockwise")

        serial_message = "DI"+str(self.step_size)

        self.serial.write(serial_message+"\r")
        self.serial.write("FL\r")

        self.current_position += self.step_size

        if self.debugging:
            print("Currently at %d steps" % self.current_position)

    def backward(self):
        if self.debugging:
            print("going counter-clockwise")

        serial_message = "DI"+str(-self.step_size)

        self.serial.write(serial_message+"\r")
        self.serial.write("FL\r")

        self.current_position -= self.step_size

        if self.debugging:
            print("Currently at %d steps" % self.current_position)

    def short(self):
        self.step_size = 1000
        if self.debugging:
            print("set step size to short, %d steps" % self.step_size)

    def long(self):
        self.step_size = 3000
        if self.debugging:
            print("set step size to long, %d steps" % self.step_size)

    def play_tone(self):
         wiringpi.softToneWrite(self.tonePin, 440)
         time.sleep(1)
         wiringpi.softToneWrite(self.tonePin,0)
         if self.debugging:
             print("Played a tone")

    def default(self):
        print("Default ")

    def go_home(self):
        if self.current_position != 0:
            hold_step_size = self.step_size
            self.step_size = abs(self.current_position)

            if self.current_position > 0:
                self.backward()
            else:
                self.forward()

            self.step_size = hold_step_size

    def stop_all(self):
        serial_message = "SK\r"
        self.serial.write(serial_message)
        if self.debugging:
            print("wrote %s to the driver" % serial_message)
            print("Stopped all and exiting!")

# Configure the serial port connection the the Si3540 motor driver

def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

availablePorts = serial_ports()
pdb.set_trace()

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
        port='/dev/ttyS0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )

ri = remote_interface(ser,debugging = True)

interpret_command = {
    "right" : ri.forward,
    "left" : ri.backward,
    "enter" : ri.go_home,
    "a" : ri.set_home,
    "b" : ri.short,
    "c" : ri.long,
    "up" : ri.play_tone,
    "quit" : ri.stop_all
}

interpret_command = defaultdict(lambda: ri.default, interpret_command)

#configure and initialize IR remote communication
blocking = 1

if(pylirc.init("training", "./conf", blocking)):

    code = {"config" : "", "repeat" : ""}

while(code["config"] != "quit"):
    #pdb.set_trace()
    # Read next code
    ir_message = pylirc.nextcode(1)
    #print("We've got mail!")

    # Loop as long as there are more on the queue
    # (dont want to wait a second if the user pressed many buttons...)
    while(ir_message):
        # Run through commands
        for (code) in ir_message:
            print("Command: %s, Repeat: %d" % (code["config"], code["repeat"]))
            #run the function returned by interpret_command
            interpret_command[code["config"]]()
            if code["config"] == "quit":
                break
        #pdb.set_trace()
        ir_message = pylirc.nextcode(1)
