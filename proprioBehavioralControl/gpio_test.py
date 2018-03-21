import RPi.GPIO as GPIO
import time

BUT1 = 4
BUT2 = 17
LED1 = 16
LED2 = 6
LED_BOTH = 12

ctrl = {
    BUT1 : LED1,
    BUT2 : LED2
    }

status = {
    BUT1 : False,
    BUT2 : False
    }

def my_callback(channel):
    print('This is a edge event callback function!')
    print('Edge detected on channel %s'%channel)
    print('This is run in a different thread to your main program')
    status[channel] = not status[channel]
    GPIO.output(ctrl[channel], status[channel])

GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
GPIO.setup(BUT1, GPIO.IN, pull_up_down = GPIO.PUD_UP) # Button pin set as input w/ pull-up
GPIO.setup(BUT2, GPIO.IN, pull_up_down = GPIO.PUD_UP) # Button pin set as input w/ pull-up
GPIO.setup(LED1, GPIO.OUT) # Button pin set as input w/ pull-up
GPIO.setup(LED2, GPIO.OUT) # Button pin set as input w/ pull-up
GPIO.setup(LED_BOTH, GPIO.OUT) # Button pin set as input w/ pull-up

GPIO.add_event_detect(BUT1, GPIO.FALLING, callback=my_callback, bouncetime=200)  # add rising edge detection on a channel
GPIO.add_event_detect(BUT2, GPIO.FALLING, callback=my_callback, bouncetime=200)  # add rising edge detection on a channel

try:
    while 1:
        time.sleep(0.5)
except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
