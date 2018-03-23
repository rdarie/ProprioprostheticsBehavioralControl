import pygame, pdb, lirc, serial, os, os.path
import logging, time, uuid, pdb, Adafruit_BluefruitLE
from helperFunctions import serial_ports

global wavePath

curfilePath = os.path.abspath(__file__)
curDir = os.path.abspath(os.path.join(curfilePath,os.pardir)) # this will return current directory in which python file resides.
parentDir = os.path.abspath(os.path.join(curDir,os.pardir)) # this will return parent directory.

with open(parentDir + '/' + '.waveLocation', 'r') as wf:
    wavePath = wf.read().replace('\n', '')

class pedalBLEInterface(object):
    def __init__(self):
        # Define service and characteristic UUIDs used by the UART service.
        Bluetooth_Base_UUID_suffix = '-0000-1000-8000-00805F9B34FB'
        self.BluetoothUUID = lambda x: '0000' + x + Bluetooth_Base_UUID_suffix

        self.TOUCH_SERVICE_UUID              = uuid.UUID(self.BluetoothUUID('A002'))
        self.TOUCH_STATE_CHARACTERISTIC_UUID = uuid.UUID(self.BluetoothUUID('A003'))
        self.MOTOR_SERVICE_UUID              = uuid.UUID(self.BluetoothUUID('A000'))
        self.MOTOR_STATE_CHARACTERISTIC_UUID = uuid.UUID(self.BluetoothUUID('A001'))

        # Get the BLE provider for the current platform.
        self.ble = Adafruit_BluefruitLE.get_provider()

        # Initialize the BLE system.  MUST be called before other BLE calls!
        self.ble.initialize()

        # Clear any cached data because both bluez and CoreBluetooth have issues with
        # caching data and it going stale.
        self.ble.clear_cached_data()

        # Get the first available BLE network adapter and make sure it's powered on.
        self.adapter = self.ble.get_default_adapter()
        self.adapter.power_on()
        print('Using adapter: {0}'.format(self.adapter.name))

        # Disconnect any currently connected UART devices.  Good for cleaning up and
        # starting from a fresh state.
        print('Disconnecting any connected Smart Pedal devices...')
        self.ble.disconnect_devices([self.TOUCH_SERVICE_UUID, self.MOTOR_SERVICE_UUID])

        # Scan for UART devices.
        print('Searching for Smart Pedal device...')
        try:
            self.adapter.start_scan()
            # Search for the first UART device found (will time out after 60 seconds
            # but you can specify an optional timeout_sec parameter to change it).
            self.device = self.ble.find_device(service_uuids=[self.TOUCH_SERVICE_UUID, self.MOTOR_SERVICE_UUID])
            if self.device is None:
                raise RuntimeError('Failed to find Smart Pedal device!')
        finally:
            # Make sure scanning is stopped before exiting.
            self.adapter.stop_scan()

        print('Connecting to device...')
        self.device.connect()  # Will time out after 60 seconds, specify timeout_sec parameter
                          # to change the timeout.

        # Wait for service discovery to complete for at least the specified
        # service and characteristic UUID lists.  Will time out after 60 seconds
        # (specify timeout_sec parameter to override).
        print('Discovering services...')
        self.device.discover([self.TOUCH_SERVICE_UUID, self.MOTOR_SERVICE_UUID], [self.TOUCH_STATE_CHARACTERISTIC_UUID, self.MOTOR_STATE_CHARACTERISTIC_UUID])

        # Find the Touch sensor service and its characteristics.
        self.touch = self.device.find_service(self.TOUCH_SERVICE_UUID)
        self.touchState = self.touch.find_characteristic(self.TOUCH_STATE_CHARACTERISTIC_UUID)
        self.motor = self.device.find_service(self.MOTOR_SERVICE_UUID)
        self.motorState = self.motor.find_characteristic(self.MOTOR_STATE_CHARACTERISTIC_UUID)

    def disconnect(self):
        # Make sure device is disconnected on exit.
        self.device.disconnect()

    def main(self):
        try:
            while True:
                time.sleep(.25)
        finally:
            self.disconnect()

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
    def __init__(self, serialPortName = '/dev/ttyUSB0',
        debugging = False, velocity = 3, acceleration = 100,
        deceleration = 100, useEncoder = False):

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
        serial_message = "MR10\r"
        self.serial.write(serial_message.encode())
        #Sets, or requests microstep resolution. The MR command should be used before setting the accel and decel rates
        #and speed, because a change in motor resolution will corrupt these settings. The MR command also
        #resets the step table, which moves the motor to the nearest pole position. The absolute position register
        #is not changed.

        self.useEncoder = useEncoder
        if useEncoder:
            serial_message = "ER6\r"
            self.serial.write(serial_message.encode())
            #On drives supporting encoder feedback, the ER command defines the encoder ratio. This number is
            #the motor resolution, in steps/rev, divided by the encoder resolution, in counts/rev.
            serial_message = "ED50\r"
            self.serial.write(serial_message.encode())
            #On drives that have the encoder feedback option, this defines the
            #size of the “in position” region. i.e. feedback is engaged if the
            #actual position is not within ED encoder counts, until it is.
            serial_message = "EF3\r"
            self.serial.write(serial_message.encode())
            #Enables static position maintenance and end of move correction
            serial_message = "EP0\r"
            self.serial.write(serial_message.encode())
            #For example, if the encoder it at 4500 counts, and you would like to refer to this position
            #as 0, send “EP0”. Sending EP with no position parameter requests the present encoder position
            #from the drive.

        self.velocity = velocity #move speed in rev/sec. Range is .025 - 50
        # note that the worm gearbox is 7.5:1 ratioed
        serial_message = "VE" + str(self.velocity) + "\r"
        self.serial.write(serial_message.encode())

        self.acceleration = acceleration #move speed in rev/sec^2.
        serial_message = "AC" + str(self.acceleration) + "\r"
        self.serial.write(serial_message.encode())

        self.deceleration = deceleration #move speed in rev/sec^2.
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

    def get_encoder_position(self):
        self.serial.write("EP\r".encode())
        epStr = self.serial.read(100)
        #print(epStr)
        epValueStr = epStr.decode().split("=")[-1]
        try:
            ep = float(epValueStr.encode()) / 4
        except:
            ep = None
        #Note: the Si™ drive electronics use “X4” decoding, so a 1000 line encoder such as the U.S. Digital
        #E2-1000-250-H produces 4000 counts/revolution.
        #therefore, divide by 4
        return ep


    def get_status(self):
        """
        M = motion in progress
        W = wait input command executing
        T = wait time command executing
        E = servo positioning fault (drive must be reset by interrupting power to clear this fault)
        R = ready (none of the above happening)
        """
        self.serial.write("RS\r".encode())
        stStr = self.serial.read(100)
        #print(epStr)
        return stStr.decode().split("=")[-1]

    def stop_all(self):
        serial_message = "SK\r"
        self.serial.write(serial_message.encode())
        if self.debugging:
            print("Stopped all and exiting!")
