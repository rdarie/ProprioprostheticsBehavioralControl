import interfaces as ifaces
import time

motor = ifaces.motorInterface(debugging = True, velocity = 3,
    acceleration = 110, deceleration = 110, useEncoder = True)
motor.step_size = 20e4
#time.sleep(10)

for i in range(2):
    motor.forward()
    #print(motor.get_encoder_position())
    motor.backward()
    #print(motor.get_encoder_position())
    doneMoving = False
    #for i in range(10):
    #    motor.get_encoder_position()
    while not doneMoving:
        curPos = motor.get_encoder_position()
        #print('Current position = %4.4f' % curPos)
        if curPos is not None: # ~ 2 degrees
            doneMoving = True
    print('Finished, at %4.4f steps' % curPos)
