import simpleaudio as sa
import pdb

class raspPiInterface(object):
    def __init__(self, serial, goWavePath, goodWavePath, debugging = False):
        self.current_position = 0

        self.step_size = 10000
        self.serial = serial

        self.goWave = sa.WaveObject.from_wave_file(goWavePath)
        self.goodWave = sa.WaveObject.from_wave_file(goodWavePath)

        self.debugging = debugging

    def set_home(self):
        self.current_position = 0
        if self.debugging:
            print("Home position was reset")

    def forward(self):
        if self.debugging:
            print("going clockwise")

        serial_message = "DI"+str(self.step_size)+"\r"

        self.serial.write(serial_message.encode())
        self.serial.write("FL\r".encode())

        self.current_position += self.step_size

        if self.debugging:
            print("Currently at %d steps" % self.current_position)

    def backward(self):
        if self.debugging:
            print("going counter-clockwise")

        serial_message = "DI"+str(-self.step_size)+"\r"

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

    # TODO: consolidate these into one play_tone function
    def play_good(self):

         play_obj = self.goodWave.play()
         play_obj.wait_done()

         if self.debugging:
             print("Played the GOOD tone")

    def play_go(self):

        play_obj = self.goWave.play()
        play_obj.wait_done()

        if self.debugging:
            print("Played the GO tone")

    def default(self):
        print("Default ")

    def go_home(self):
        if self.current_position != 0:
            hold_step_size = self.step_size
            self.step_size = abs(self.current_position)

            if self.debugging:
                print("Going home! ")

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

# Configure the serial port connection the the Si3540 motor driver
