import interfaces as ifaces
import time

motor = ifaces.motorInterface(debugging = True)

while True:
	motor.step_size = 5e4
	motor.forward()
	time.sleep(5)
