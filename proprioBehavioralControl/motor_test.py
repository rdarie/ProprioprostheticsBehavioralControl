import interfaces as ifaces
import time

motor = ifaces.motorInterface(debugging = True, velocity = 3.3,
    acceleration = 110, deceleration = 110, useEncoder = True)
motor.step_size = 10e4
time.sleep(10)

for i in range(10):
    motor.forward()
    time.sleep(2)
    motor.backward()
    time.sleep(2)
