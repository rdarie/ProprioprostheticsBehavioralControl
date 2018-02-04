import interfaces as ifaces
import time

motor = ifaces.motorInterface(debugging = True, velocity = 3.3,
    acceleration = 110, deceleration = 110, useEncoder = True)
motor.step_size = 10e4
#time.sleep(10)

for i in range(10):
    motor.forward()
    motor.get_encoder_position()
    motor.backward()
    motor.get_encoder_position()
    doneMoving = False
    #for i in range(10):
    #    motor.get_encoder_position()
    #while not doneMoving:
    #    curPos = motor.get_encoder_position()
    #    #print('Current position = %4.4f' % curPos)
    #    if curPos < 5: # ~ 2 degrees
    #        doneMoving = True
