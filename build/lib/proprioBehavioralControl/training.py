#! /usr/bin/env python3

import lirc, serial
from collections import defaultdict
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

        # Loop as long as there are more on the queue
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
