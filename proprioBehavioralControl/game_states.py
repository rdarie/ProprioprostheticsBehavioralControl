import sys, random, time, pdb, shutil
import numpy as np
from helperFunctions import overRideAdder
from collections import OrderedDict

nominalBlockLength  = 2

class gameState(object):
    def __init__(self, nextState, parent, stateName, logFile = None):
        self.nextState = nextState

        self.enableLog = True
        self.firstVisit = True

        self.sleepTime = 0.05
        self.timeNow = time.time()
        self.timedOut = False
        self.nextTimeOut = 0

        self.payload = np.nan

        self.logFile = logFile
        self.parent = parent
        self.__name__ = stateName

    def operation(self, parent):
        pass

    def checkTimedOut(self):
        self.timeNow = time.time()

        if self.nextTimeOut < self.timeNow:
            self.timedOut = True

    def __call__(self, *args):

        if self.parent.remoteOverride is None:
            #print("in Python: Override is none! I am %s" % self.__name__)
            ret = self.operation(self.parent)
        else:
            #print("in Python: Override is NOT none! I am %s" % self.__name__)
            ret = self.parent.remoteOverride
            self.enableLog = True
            self.parent.remoteOverride = None
        #print("returning %s" % ret)
        if self.logFile:
            if self.enableLog:
                self.timeNow = time.time()
                logData = {
                    'name' : self.__name__,
                    'time' :  self.timeNow,
                    'payload': self.payload
                    }
                self.logFile.write(logData)

        return ret

class fixation(gameState):

    def operation(self, parent):
        self.checkTimedOut()

        if self.firstVisit:
            self.nextTimeOut = self.timeNow + parent.trialLength

        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (self.nextTimeOut - self.timeNow))
        sys.stdout.flush()

        time.sleep(self.sleepTime)

        if self.timedOut:
            #leaving fixation, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            print(' ')
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
        if self.firstVisit:
            print('Started strict fixation')
            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.trialLength
            self.enableLog = False
            self.firstVisit = False

        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (self.nextTimeOut - self.timeNow))
        sys.stdout.flush()

        self.checkTimedOut()

        time.sleep(self.sleepTime)
        # Read from inbox
        event_label = parent.request_last_touch()

        if event_label:
            # if erroneous button press, play bad tone, and penalize with an extra
            # 2 second wait
            parent.speaker.play_tone('Wait')
            time.sleep(3)
            self.nextTimeOut = self.nextTimeOut + 3
            # clear button queue for next iteration
            if parent.inputPin.last_data is not None:
                parent.inputPin.last_data = None

        if self.timedOut:
            #leaving fixation, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            print(' ')
            return self.nextState[0]
        else:
            # not yet enabled
            #disable logging for subsequent visits to this state, until we leave it
            self.enableLog = False
            self.firstVisit = False
            return self.nextState[1]

class turnPedalRandom(gameState):

    def operation(self, parent):
        # should we add time penalties for button presses?
        enforceWait = True if parent.lastCategory is not None else False

        if parent.lastCategory is None:
            # this is the first throw

            if parent.blocsRemaining == 0:
                #start a new block!

                #switch block category
                category = 'small' if parent.initBlocType['category'] == 'big' else 'big'

                #set the block category for the rest of the block
                parent.initBlocType['category'] = category
            else:
                # repeat the last block type
                category = parent.initBlocType['category']

            parent.lastCategory = category
        else:
            # this is the second throw; do the opposite of the first one
            category = 'big' if parent.lastCategory == 'small' else 'small'
            parent.lastCategory = None

        parent.motor.step_size = random.uniform(1e4, 1.5e4) if category == 'small'\
            else random.uniform(6.5e4, 7e4)

        if parent.lastDirection is None:
            # this is the first throw

            if parent.blocsRemaining == 0:
                #start a new block!

                #set the block direction for the rest of the block
                direction = 'forward' if bool(random.getrandbits(1)) else 'backward'
                parent.initBlocType['direction'] = direction

                # re-evaluate the block lengths
                smallProp = (parent.smallTally) / (parent.bigTally + parent.smallTally)
                bigProp = (parent.bigTally) / (parent.bigTally + parent.smallTally)

                bias = smallProp - bigProp # positive if biased towards the small, negative otherwise
                smallProp = 0.5 - 2 * bias # if biased towards small, give fewer small draws
                bigProp = 0.5 + 2 * bias # opposite

                parent.smallBlocLength = round(nominalBlockLength * bigProp) + 1
                print('\nUpdated mean number of small throws to : %d' % parent.smallBlocLength)
                parent.bigBlocLength = round(nominalBlockLength * smallProp) + 1
                print('\nUpdated mean number of big throws to : %d' % parent.bigBlocLength)

                smallDraw = round(random.gauss(parent.smallBlocLength, 1.5))
                if smallDraw <= 0:
                    smallDraw = 1

                bigDraw = round(random.gauss(parent.bigBlocLength, 1.5))
                if bigDraw <= 0:
                    bigDraw = 1

                parent.blocsRemaining = smallDraw if parent.initBlocType['category'] == 'small' else bigDraw

                print('\nUpdated number of throws for next block to : %d' % parent.blocsRemaining)
            else:
                direction = parent.initBlocType['direction']
                parent.blocsRemaining = parent.blocsRemaining - 1

            parent.lastDirection = direction
        else:
            direction = 'forward' if parent.lastDirection == 'forward' else 'backward'
            parent.lastDirection = None

        if direction == 'forward':
            parent.motor.forward()
            if self.logFile:
                self.payload = parent.motor.step_size
        else:
            parent.motor.backward()
            if self.logFile:
                self.payload = -parent.motor.step_size

        parent.motor.go_home()
        parent.magnitudeQueue.append(parent.motor.step_size)

        if parent.motor.useEncoder:
            doneMoving = False
            while not doneMoving:
                curPos = parent.motor.get_encoder_position()
                time.sleep(0.1)
                #print('Current position = %4.4f' % curPos)
                if curPos is not None:
                    doneMoving = True
            sleepTime = 0.05
        else:
            sleepTime = 2

        while sleepTime > 0:
            # Read from inbox
            event_label = parent.request_last_touch()
            time.sleep(0.05)
            sleepTime = sleepTime - 0.05

            if event_label and enforceWait:
                # if erroneous button press, play bad tone, and penalize with an extra
                # 500 millisecond wait
                parent.speaker.play_tone('Wait')
                sleepTime = sleepTime + 0.5
                # clear button queue for next iteration
                if parent.inputPin.last_data is not None:
                    parent.inputPin.last_data = None

        return self.nextState[0]

class turnPedalCompound(gameState):

    def operation(self, parent):
        # should we add time penalties for button presses?
        enforceWait = True

        if parent.blocsRemaining == 0:
            #start a new block!

            #switch block category
            category = 'small' if parent.initBlocType['category'] == 'big' else 'big'

            #set the block category for the rest of the block
            parent.initBlocType['category'] = category

            #set the block direction for the rest of the block
            direction = 'forward' if bool(random.getrandbits(1)) else 'backward'
            parent.initBlocType['direction'] = direction

            # re-evaluate the block lengths
            smallProp = (parent.smallTally) / (parent.bigTally + parent.smallTally)
            bigProp = (parent.bigTally) / (parent.bigTally + parent.smallTally)

            bias = smallProp - bigProp # positive if biased towards the small, negative otherwise
            smallProp = 0.5 - 2 * bias # if biased towards small, give fewer small draws
            bigProp = 0.5 + 2 * bias # opposite

            parent.smallBlocLength = round(nominalBlockLength * bigProp) + 1
            print('\nUpdated mean number of small throws to : %d' % parent.smallBlocLength)
            parent.bigBlocLength = round(nominalBlockLength * smallProp) + 1
            print('\nUpdated mean number of big throws to : %d' % parent.bigBlocLength)

            smallDraw = round(random.gauss(parent.smallBlocLength, 1.5))
            if smallDraw <= 0:
                smallDraw = 1

            bigDraw = round(random.gauss(parent.bigBlocLength, 1.5))
            if bigDraw <= 0:
                bigDraw = 1

            parent.blocsRemaining = smallDraw if parent.initBlocType['category'] == 'small' else bigDraw

            print('\nUpdated number of throws for next block to : %d' % parent.blocsRemaining)
        else:
            # repeat the last block type
            category = parent.initBlocType['category']
            direction = parent.initBlocType['direction']
            parent.blocsRemaining = parent.blocsRemaining - 1

        parent.motor.step_size = random.uniform(1e4, 1.5e4) if category == 'small'\
            else random.uniform(6.5e4, 7e4)

        self.payload = {'firstThrow': 0, 'secondThrow' : 0}
        if direction == 'forward':
            parent.motor.forward()
            if self.logFile:
                self.payload['firstThrow'] = parent.motor.step_size
        else:
            parent.motor.backward()
            if self.logFile:
                self.payload['firstThrow'] = -parent.motor.step_size

        parent.motor.go_home()
        parent.magnitudeQueue.append(parent.motor.step_size)

        ## Second Movement
        ## TODO: Sleep the parent some number of milliseconds
        ## TODO: fix logging
        parent.motor.step_size = random.uniform(6.5e4, 7e4) if category == 'small'\
            else random.uniform(1e4, 1.5e4)

        if direction == 'forward':
            parent.motor.forward()
            if self.logFile:
                self.payload['secondThrow'] = parent.motor.step_size
        else:
            parent.motor.backward()
            if self.logFile:
                self.payload['secondThrow'] = -parent.motor.step_size

        parent.motor.go_home()
        parent.magnitudeQueue.append(parent.motor.step_size)
        parent.motor.serial.write("WT0.3".encode())

        #Obviate the need to stop by the set_correct state
        parent.correctButton = 'red'\
            if parent.magnitudeQueue[0] < parent.magnitudeQueue[1]\
            else 'green'

        print('  ')
        print('Correct button set to: %s' % parent.correctButton)

        if parent.motor.useEncoder:
            doneMoving = False
            while not doneMoving:
                curPos = parent.motor.get_encoder_position()
                time.sleep(0.1)
                #
                if curPos is not None:
                    doneMoving = True
                    print('Current position = %4.4f' % curPos)
            sleepTime = 0.05
        else:
            sleepTime = 2

        while sleepTime > 0:
            # Read from inbox
            event_label = parent.request_last_touch()
            time.sleep(0.05)
            sleepTime = sleepTime - 0.05

            if event_label and enforceWait:
                # if erroneous button press, play bad tone, and penalize with an extra
                # 500 millisecond wait
                parent.speaker.play_tone('Wait')
                sleepTime = sleepTime + 0.5
                # clear button queue for next iteration
                if parent.inputPin.last_data is not None:
                    parent.inputPin.last_data = None

        # obviate the need to go to clear_input_queue
        if parent.inputPin.last_data is not None:
            parent.inputPin.last_data = None
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

class chooseNextTrial(gameState):

    def operation(self, parent):
        bins = [0, 1/8, 1]
        draw = random.uniform(0,1)
        return self.nextState[int(np.digitize(draw, bins) - 1)]

class set_correct(gameState):

    def operation(self, parent):
        parent.correctButton = 'red'\
            if parent.magnitudeQueue[0] < parent.magnitudeQueue[1]\
            else 'green'

        print('  ')
        print('Correct button set to: %s' % parent.correctButton)

        return self.nextState[0]

class wait_for_any_button(gameState):
    def operation(self, parent):
        # Read from inbox
        event_label = parent.request_last_touch()

        if event_label:
            if self.logFile:
                self.logFile.write("\ncorrect button\t%s\t" % event_label)
            print("\n%s button pressed!" % event_label)

            #leaving wait_for_button, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            return self.nextState[0]
        else:
            time.sleep(self.sleepTime)

            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()

            self.enableLog = False
            self.firstVisit = False
            return 'wait_for_any_button'

class wait_for_any_button_timed(gameState):
    def operation(self, parent):

        if self.firstVisit:
            print('Started Timed Button')
            # Turn LED's On
            parent.outbox.put('redLED')
            parent.outbox.put('greenLED')

            self.firstVisit = False
            self.enableLog = False

            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.trialTimeout
        # Read from inbox
        event_label = parent.request_last_touch()

        self.checkTimedOut()

        if event_label:
            if self.logFile:
                self.logFile.write("\ncorrect button\t%4.4f\t%s" % (self.timeNow, event_label))
            print("\n%s button pressed!" % event_label)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('redLED')
            parent.outbox.put('greenLED')
            print(' ')
            return self.nextState[0] # usually the good state

        if self.timedOut:
            if self.logFile:
                self.logFile.write("\nbutton timed out\t %4.4f\t" % self.timeNow)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('redLED')
            parent.outbox.put('greenLED')
            print(' ')
            # re enable logging for future visits
            return self.nextState[1] # usually the post-trial state

        else: # if not parent.buttonTimedOut
            time.sleep(self.sleepTime)

            sys.stdout.write("Waiting for button... Time left: %4.4f \r" %
                (self.nextTimeOut - self.timeNow))
            sys.stdout.flush()

            return self.nextState[2]

class wait_for_correct_button_timed(gameState):
    def operation(self, parent):

        if self.firstVisit:
            print('Started Timed Button')
            # Turn LED's On
            parent.outbox.put('redLED' if parent.correctButton == 'red' else 'greenLED')

            self.firstVisit = False
            self.enableLog = False

            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.trialTimeout

            if parent.easyReward is not None:
                parent.juicePin.instructions =\
                    ['flip', 'flip', ('pulse', parent.easyReward)]
        # Read from inbox
        event_label = parent.request_last_touch()

        self.checkTimedOut()

        if event_label:

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('redLED' if parent.correctButton == 'red' else 'greenLED')

            print(' ')

            if event_label == 'red':
                parent.smallTally = parent.smallTally * 0.9 + 1
            else:
                parent.bigTally = parent.bigTally * 0.9 + 1

            if event_label == parent.correctButton:
                if self.logFile:
                    self.logFile.write("\ncorrect button\t%4.4f\t%s" % (self.timeNow, event_label))
                print("\n%s button pressed correctly!" % event_label)
                return self.nextState[0] # usually the good state
            else:
                if self.logFile:
                    self.logFile.write("\nincorrect button\t%4.4f\t%s" % (self.timeNow, event_label))
                print("\n%s button pressed incorrectly!" % event_label)
                return self.nextState[1] # usually the good state

        if self.timedOut:
            if self.logFile:
                self.logFile.write("\nbutton timed out\t %4.4f\t" % self.timeNow)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('redLED' if parent.correctButton == 'red' else 'greenLED')

            print(' ')
            # re enable logging for future visits
            return self.nextState[1] # usually the post-trial state

        else: # if not parent.buttonTimedOut
            time.sleep(self.sleepTime)

            sys.stdout.write("Waiting for button... Time left: %4.4f \r" %
                (self.nextTimeOut - self.timeNow))
            sys.stdout.flush()

            return self.nextState[2]

class wait_for_correct_button_timed_uncued(gameState):
    def operation(self, parent):

        if self.firstVisit:
            print('Started Timed Button')
            # Turn LED's On
            parent.outbox.put('redLED')
            parent.outbox.put('greenLED')

            self.firstVisit = False
            self.enableLog = False

            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.trialTimeout

            if parent.hardReward is not None:
                parent.juicePin.instructions =\
                    ['flip', 'flip', ('pulse', parent.hardReward)]
        # Read from inbox
        event_label = parent.request_last_touch()

        self.checkTimedOut()

        if event_label:

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('redLED')
            parent.outbox.put('greenLED')

            print(' ')

            if event_label == 'red':
                parent.smallTally = 0.9 * parent.smallTally + 1
            else:
                parent.bigTally = 0.9 * parent.bigTally + 1

            if event_label == parent.correctButton:
                if self.logFile:
                    self.logFile.write("\ncorrect button\t%4.4f\t%s" % (self.timeNow, event_label))
                print("\n%s button pressed correctly!" % event_label)
                return self.nextState[0] # usually the good state
            else:
                if self.logFile:
                    self.logFile.write("\nincorrect button\t%4.4f\t%s" % (self.timeNow, event_label))
                print("\n%s button pressed incorrectly!" % event_label)
                return self.nextState[1] # usually the good state

        if self.timedOut:
            if self.logFile:
                self.logFile.write("\nbutton timed out\t %4.4f\t" % self.timeNow)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('redLED')
            parent.outbox.put('greenLED')

            print(' ')
            # re enable logging for future visits
            return self.nextState[1] # usually the post-trial state

        else: # if not parent.buttonTimedOut
            time.sleep(self.sleepTime)

            sys.stdout.write("Waiting for button... Time left: %4.4f \r" %
                (self.nextTimeOut - self.timeNow))
            sys.stdout.flush()

            return self.nextState[2]


class wait_for_correct_button(gameState):

    def operation(self, parent):
        # Read from inbox
        event_label = parent.request_last_touch()

        if self.firstVisit:
            self.firstVisit = False
            self.enableLog = False

        if event_label:
            if self.logFile:
                self.logFile.write("\nbutton pressed\t%s\t" % event_label)
            print("\n%s button pressed!" % event_label)

            nextFun = self.nextState[0] if parent.correctButton == event_label else self.nextState[1]

            self.firstVisit = True
            self.enableLog = True
            return nextFun
        else:
            time.sleep(self.sleepTime)
            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()
            return 'wait_for_correct_button'

class good(gameState):
    # TODO: add amount dispensed to log
    def operation(self, parent):
        print('Good job!')
        parent.trialLength = parent.nominalTrialLength
        parent.outbox.put('Reward')
        parent.speaker.play_tone('Good')
        return self.nextState[0]

class bad(gameState):

    def operation(self, parent):
        print('Wrong! Try again!')
        parent.trialLength = parent.nominalTrialLength + parent.wrongTimeout
        parent.speaker.play_tone('Bad')
        return self.nextState[0]

class post_trial(gameState):

    def operation(self, parent):
        print('At post trial')
        parent.magnitudeQueue = []
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
