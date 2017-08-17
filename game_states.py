import sys, random, time, pdb, shutil
from helperFunctions import overRideAdder
from random import uniform, randint

class gameState(object):
    def __init__(self, nextState, parent, stateName, logFile = None):
        self.nextState = nextState
        self.enableLog = True
        self.firstVisit = True
        self.logFile = logFile
        self.parent = parent
        self.__name__ = stateName

    def operation(self, parent):
        pass

    def __call__(self, *args):

        if self.logFile:
            if self.enableLog:
                timeNow = time.time()
                self.logFile.write("\n%s\t%4.4f" % ( self.__name__, timeNow))

        if self.parent.remoteOverride is None:
            #print("in Python: Override is none! I am %s" % self.__name__)
            ret = self.operation(self.parent)
        else:
            #print("in Python: Override is NOT none! I am %s" % self.__name__)
            ret = self.parent.remoteOverride
            self.enableLog = True
            self.parent.remoteOverride = None
        #print("returning %s" % ret)
        return ret

class fixation(gameState):

    def operation(self, parent):
        timeNow = time.time()

        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (parent.nextEnableTime - timeNow))
        sys.stdout.flush()

        time.sleep(0.5)

        if parent.nextEnableTime < timeNow:
            parent.startEnable = True

        if parent.startEnable:
            #leaving fixation, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            parent.startEnable = False
            return self.nextState[0]
        else:
            # not yet enabled
            #disable logging for subsequent visits to this state, until we leave it
            self.enableLog = False
            self.firstVisit = False
            return self.nextState[1]

class strict_fixation(gameState):
    # IF button presses happen here, give bad feedback
    def operation(self, parent):
        timeNow = time.time()

        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (parent.nextEnableTime - timeNow))
        sys.stdout.flush()

        time.sleep(0.25)
        # Read from inbox
        event_label = parent.request_last_touch()
        if event_label:
            parent.speaker.play_tone('Bad')
            time.sleep(2)
            parent.nextEnableTime = parent.nextEnableTime + 2
            if parent.inputPin.last_data is not None:
                parent.inputPin.last_data = None

        if parent.nextEnableTime < timeNow:
            parent.startEnable = True

        if parent.startEnable:
            #leaving fixation, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            parent.startEnable = False
            return self.nextState[0]
        else:
            # not yet enabled
            #disable logging for subsequent visits to this state, until we leave it
            self.enableLog = False
            self.firstVisit = False
            return self.nextState[1]

class turnPedalRandom(gameState):

    def operation(self, parent):

        #parent.speaker.play_tone('Go')
        #time.sleep(0.5)
        #parent.speaker.play_tone('Go')
        #time.sleep(5)

        parent.motor.step_size = uniform(2e4, 4e4)

        direction = randint(0, 1)
        if direction:
            parent.motor.forward()
        else:
            parent.motor.backward()

        time.sleep(1.5)
        parent.motor.go_home()
        time.sleep(1.5)
        return self.nextState[0]

class clear_input_queue(gameState):

    def operation(self, parent):
        # clear the button inputs queue
        # TODO: Make this thread safe
        if parent.inputPin.last_data is not None:
            parent.inputPin.last_data = None
        return self.nextState[0]

class trial_start(gameState):

    def operation(self, parent):
        parent.speaker.play_tone('Go')
        print('Trial Started!')
        return self.nextState[0]

class set_correct(gameState):

    def operation(self, parent):
        parent.correctButton = 'red' if random.randint(0,1) == 0 else 'blue'
        print('  ')
        print('Correct button set to: %s' % parent.correctButton)

        return self.nextState[0]

class wait_for_any_button(gameState):
    def operation(self, parent):
        # Read from inbox
        event_label = parent.request_last_touch()

        if event_label:
            if self.logFile:
                self.logFile.write("\ncorrect_button\t%s\t" % event_label)
            print("\n%s button pressed!" % event_label)

            #leaving wait_for_button, turn logging on for next return to fixation
            self.enableLog = True
            self.fistVisit = True
            return self.nextState[0]
        else:
            time.sleep(0.1)

            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()

            self.enableLog = False
            self.fistVisit = False
            return 'wait_for_any_button'

class wait_for_any_button_timed(gameState):
    def operation(self, parent):
        # Read from inbox
        event_label = parent.request_last_touch()

        timeNow = time.time()
        if not self.firstVisit:
            if parent.nextButtonTimeout < timeNow:
                parent.buttonTimedOut = True
        else:
            # Turn LED's On
            parent.outbox.put('redLED')
            parent.outbox.put('blueLED')

        if event_label:
            if self.logFile:
                self.logFile.write("\ncorrect_button\t%4.4f\t%s" % (timeNow, event_label))
            print("\n%s button pressed!" % event_label)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.fistVisit = True
            parent.buttonTimedOut = False
            return self.nextState[0]

        if parent.buttonTimedOut:
            if self.logFile:
                self.logFile.write("\nbutton timed out!\t %4.4f\t" % timeNow)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.fistVisit = True
            parent.buttonTimedOut = False
            # re enable logging for future visits
            return self.nextState[1]
        else: # if not parent.buttonTimedOut

            time.sleep(0.1)
            if self.firstVisit:
                self.firstVisit = False
                self.enableLog = False
                parent.nextButtonTimeout = timeNow + parent.trialTimeout

            sys.stdout.write("Waiting for button... Time left: %4.4f \r" %
                (parent.nextButtonTimeout - timeNow))
            sys.stdout.flush()

            return 'wait_for_any_button_timed'


class wait_for_correct_button(gameState):
    def operation(self, parent):
        # Read from inbox
        event_label = parent.request_last_touch()

        self.firstVisit = False
        self.enableLog = False
        if event_label:
            if self.logFile:
                self.logFile.write("\nbutton_pressed\t%s\t" % event_label)
            print("\n%s button pressed!" % event_label)
            nextFun = self.nextState[0] if parent.correctButton == event_label else self.nextState[1]
            self.firstVisit = True
            self.enableLog = True
            return nextFun
        else:
            time.sleep(0.01)
            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()
            return 'wait_for_correct_button'

class good(gameState):

    def operation(self, parent):
        print('Good job!')
        parent.outbox.put('Reward')
        parent.speaker.play_tone('Good')
        return self.nextState[0]

class bad(gameState):

    def operation(self, parent):
        print('Wrong! Try again!')
        parent.speaker.play_tone('Bad')
        return self.nextState[0]

class post_trial(gameState):

    def operation(self, parent):
        parent.nextEnableTime = time.time() + parent.trialLength
        parent.outbox.put('redLED')
        parent.outbox.put('blueLED')
        return self.nextState[0]

class end(gameState):

    def operation(self, parent):

        print('@game_states.py, end')
        return self.nextState[0]

class do_nothing(gameState):

    def operation(self, parent):
        #parent.enableLog = False
        time.sleep(1)
        return self.nextState[0]
