import interfaces as ifaces

motor = ifaces.motorInterface(debugging = True)

for i in range(10):
    motor.forward()
    motor.backward()
