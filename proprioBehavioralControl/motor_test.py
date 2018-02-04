import interfaces as ifaces
import time

motor = ifaces.motorInterface(debugging = True, velocity = 6, acceleration = 300, deceleration = 300)
motor.step_size = 7e4

for i in range(10):
    motor.forward()
    time.sleep(1)
    motor.backward()
    time.sleep(1)
    print('done')
