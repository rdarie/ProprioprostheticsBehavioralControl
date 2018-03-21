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
    LED1 : False,
    LED2 : False,
    LED_BOTH : False
    }

def my_callback(channel):
    print('This is a edge event callback function!')
    print('Edge detected on channel %s'%channel)
    print('This is run in a different thread to your main program')
    status[ctrl[channel]] = not status[ctrl[channel]]
    GPIO.output(ctrl[channel], status[ctrl[channel]])

GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme

GPIO.setup(BUT1, GPIO.IN, pull_up_down = GPIO.PUD_DOWN) # Button pin set as input w/ pull-up
GPIO.setup(BUT2, GPIO.IN, pull_up_down = GPIO.PUD_DOWN) # Button pin set as input w/ pull-up

GPIO.setup(LED1, GPIO.OUT) # Button pin set as input w/ pull-up
GPIO.setup(LED2, GPIO.OUT) # Button pin set as input w/ pull-up
GPIO.setup(LED_BOTH, GPIO.OUT) # Button pin set as input w/ pull-up

GPIO.output(LED1, 0)
GPIO.output(LED2, 0)
GPIO.output(LED_BOTH, 0)

GPIO.add_event_detect(BUT1, GPIO.FALLING, callback=my_callback, bouncetime=200)  # add rising edge detection on a channel
GPIO.add_event_detect(BUT2, GPIO.FALLING, callback=my_callback, bouncetime=200)  # add rising edge detection on a channel

try:
    while 1:
        time.sleep(0.5)
        #status[LED_BOTH] = not status[LED_BOTH]
        #GPIO.output(LED_BOTH, status[LED_BOTH])
        status[LED1] = not status[LED1]
        GPIO.output(LED1, status[LED1])
        status[LED2] = not status[LED2]
        GPIO.output(LED2, status[LED2])

except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    GPIO.cleanup() # cleanup all GPIO
