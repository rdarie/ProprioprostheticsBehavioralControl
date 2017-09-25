import RPi.GPIO as GPIO
import time

def my_callback(channel):
    print('This is a edge event callback function!')
    print('Edge detected on channel %s'%channel)
    print('This is run in a different thread to your main program')

butPin = 17 # Broadcom pin 17 (P1 pin 11)
GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
GPIO.setup(butPin, GPIO.IN, pull_up_down = GPIO.PUD_UP) # Button pin set as input w/ pull-up

GPIO.add_event_detect(butPin, GPIO.FALLING, callback=my_callback, bouncetime=200)  # add rising edge detection on a channel

try:
    while 1:
        time.sleep(0.5)
except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
