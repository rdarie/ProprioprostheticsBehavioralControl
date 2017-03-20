import simpleaudio as sa

class sparkfunRemoteInterface(object):
    def __init__(self, serial,goWavePath, debugging = False):
        self.current_position = 0

        self.step_size = 10000
        self.serial = serial

        self.wave_obj = sa.WaveObject.from_wave_file(goWavePath)

        self.debugging = debugging

    def set_home(self):
        self.current_position = 0
        if self.debugging:
            print("Home position was reset")

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

         play_obj = self.wave_obj.play()
         play_obj.wait_done()

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
