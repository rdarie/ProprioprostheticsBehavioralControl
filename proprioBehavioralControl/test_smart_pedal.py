from interfaces import pedalBLEInterface

pedal = pedalBLEInterface()
print('Finished starting the pedal')
pedal.motorState.write_value([1])
time.sleep(1)
pedal.motorState.write_value([0])

# Function to receive RX characteristic changes.  Note that this will
# be called on a different thread so be careful to make sure state that
# the function changes is thread safe.  Use queue or other thread-safe
# primitives to send data to other threads.
def received(data):
    print('Received: {0}'.format(ord(data)))

# Turn on notification of RX characteristics using the callback above.
print('Subscribing to RX characteristic changes...')
pedal.touchState.start_notify(received)
pdb.set_trace()
try:
    while True:
        pass
finally:
    pedal.disconnect()
