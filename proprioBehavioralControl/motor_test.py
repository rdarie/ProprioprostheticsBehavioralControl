import interfaces as ifaces
import time

<<<<<<< HEAD
motor = ifaces.motorInterface(debugging = True, velocity = 6, acceleration = 300, deceleration = 300)
motor.step_size = 7e4

for i in range(10):
    motor.forward()
    time.sleep(1)
    motor.backward()
    time.sleep(1)
    print('done')
=======
motor = ifaces.motorInterface(debugging = True, velocity = 3.3,
    acceleration = 110, deceleration = 110, useEncoder = True)
motor.step_size = 10e4
time.sleep(10)

for i in range(10):
    motor.forward()
    motor.backward()
    doneMoving = False
    while not doneMoving:
        curPos = parent.motor.get_encoder_position()
        print('Current position = %4.4f' % curPos)
        if curPos < 5 # ~ 2 degrees
            doneMoving = True
>>>>>>> 852eca21edf1874efcd4d68864defb49af7ebda1
