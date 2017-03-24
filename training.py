#! /usr/bin/env python3

import lirc, serial
from collections import defaultdict
from sparkfunRemote import sparkfunRemoteInterface as SRI
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

print(ser.port)
ri = SRI(ser,goWavePath = "go_cue.wav", debugging = True)

interpret_command = {
    "right" : ri.forward,
    "left" : ri.backward,
    "enter" : ri.go_home,
    "a" : ri.set_home,
    "b" : ri.play_go,
    "up" : ri.shorten,
    "down" : ri.lengthen,
    "quit" : ri.stop_all
}

interpret_command = defaultdict(lambda: ri.default, interpret_command)

#configure and initialize IR remote communication
blocking = 1

code = "start"

if(lirc.init("training", "./conf", blocking)):

    while(code != "quit"):
        #pdb.set_trace()
        # Read next code
        ir_message = lirc.nextcode()
        #print("We've got mail!")

        # Loop as long as there are more on the queue
        # (dont want to wait a second if the user pressed many buttons...)
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
