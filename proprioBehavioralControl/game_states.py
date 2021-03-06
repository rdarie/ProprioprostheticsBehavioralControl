import sys, random, time, pdb, shutil
import numpy as np
from helperFunctions import overRideAdder
from collections import OrderedDict

nominalBlockLength = 2
def waitUntilDoneMoving(motor):

    doneMoving = False
    while not doneMoving:
        curStatus = motor.get_status()
        #print('Current Status = %s' % curStatus)
        if 'R' in curStatus:
            doneMoving = True
            print('Done moving')
            break

    return doneMoving

class gameState(object):
    def __init__(
            self, nextState, parent, stateName,
            logFile = None, printStatements = False):
        self.nextState = nextState

        self.enableLog = True
        self.firstVisit = True
        self.printStatements = printStatements

        self.sleepTime = 0.05
        self.timeNow = time.time()
        self.timedOut = False
        self.nextTimeOut = 0

        self.payload = None

        self.logFile = logFile
        self.parent = parent
        self.__name__ = stateName

    def operation(self, parent):
        pass

    def checkTimedOut(self):
        self.timeNow = time.time()
        if self.nextTimeOut < self.timeNow:
            self.timedOut = True

    def logEvent(self, eventName, eventPayload):
        self.timeNow = time.time()
        logData = {
            'Label' : eventName,
            'Time' :  time.time(),
            'Details': eventPayload
            }
        self.logFile.write(logData)

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
        if self.logFile and self.enableLog:
            self.logEvent(self.__name__, self.payload)

        return ret

class fixation(gameState):

    def operation(self, parent):
        self.checkTimedOut()

        if self.firstVisit:
            self.nextTimeOut = self.timeNow + parent.fixationDur

        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (self.nextTimeOut - self.timeNow))
        sys.stdout.flush()

        time.sleep(self.sleepTime)

        if self.timedOut:
            #leaving fixation, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            if self.printStatements:
                print(' ')
            return self.nextState[0]
        else:
            # not yet enabled
            #disable logging for subsequent visits to this state, until we leave it
            self.enableLog = False
            self.firstVisit = False
            return self.nextState[1]

class strict_fixation(gameState):
    def __init__(
            self, nextState, parent, stateName,
            logFile=None, printStatements=False, timePenalty=0):
        super().__init__(
            nextState, parent, stateName,
            logFile=logFile, printStatements=printStatements)
        self.timePenalty = timePenalty
    
    # IF button presses happen here, give bad feedback
    def operation(self, parent):
        if self.firstVisit:
            if self.printStatements:
                print('Started strict fixation')
            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.fixationDur
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
            #  if erroneous button press, play wait tone
            #  and penalize with an extra
            #  self.timePenalty seconds wait
            parent.speaker.play_tone('Wait')
            time.sleep(self.timePenalty)
            self.nextTimeOut = self.nextTimeOut + self.timePenalty
            # clear button queue for next iteration
            if parent.inputPin.last_data is not None:
                parent.inputPin.last_data = None

        if self.timedOut:
            #leaving fixation, turn logging on for next return to fixation
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            if self.printStatements:
                print(' ')
            return self.nextState[0]
        else:
            # not yet enabled
            #disable logging for subsequent visits to this state, until we leave it
            self.enableLog = False
            self.firstVisit = False
            return self.nextState[1]

class turnPedalCompoundWithStim(gameState):
    def __init__(
            self, nextState, parent, stateName,
            logFile=None, printStatements=False,
            # phantom=False, 
            timePenalty=0,
            smallProba=0.5, cWProba=0.5,
            angleJitter=5e2, waitAtPeak=0.5):
        super().__init__(
            nextState, parent, stateName,
            logFile=logFile, printStatements=printStatements)
        # self.phantom = phantom
        self.timePenalty = timePenalty
        self.smallProba = smallProba
        self.cWProba = cWProba
        self.angleJitter = angleJitter
        self.waitAtPeak = waitAtPeak
        
    def operation(self, parent):
        #
        categDraw = random.random()
        category = 'small' if categDraw < self.smallProba else 'big'
        dirDraw = random.random()
        direction = 'forward' if dirDraw < self.cWProba else 'backward'
        # re-evaluate the block lengths
        leftProp = (parent.leftTally) / (parent.leftTally + parent.rightTally)
        # self.smallProba = 1 - leftProp
        self.smallProba = leftProp
        #
        if self.printStatements:
            print('\ntally of left choices is : %4.2f' % parent.leftTally)
            print('\ntally of right choices is : %4.2f' % parent.rightTally)
            print('\nprobability to draw small is : %4.2f' % self.smallProba)
        #
        # Draw a pair of indices into SM.magnitudes and set the first throw to the first magnitude
        magnitudeIndex = random.choice(parent.movementSets[category])
        parent.jackpot = magnitudeIndex in parent.jackpotSets
        # initialize in case there is no parent.summit
        frequency = 999
        progIdx = 999
        altProgIdx = 999
        expectedMovementDuration = 0

        if parent.summit:
            # choose a frequency for this trial
            frequency = random.choice(parent.stimFreqs)
            parent.summit.freqChange(frequency)
            time.sleep(0.5)

        def executeMovement(
                stepSize):
            parent.motor.step_size = stepSize
            print('Set movement magnitude to : %4.2f' % parent.motor.step_size)
            if parent.dummyMotor:
                parent.dummyMotor.step_size = max(parent.movementMagnitudes) - stepSize
            # 9/44 is the gearing ratio
            expectedMovementDuration = (
            parent.motor.step_size / (100 * 360) /
            (parent.motor.velocity * (9/44)) + self.waitAtPeak / 2)
            if parent.summit:
                # choose an electrode for this stim
                progSetName = random.choices(parent.progNames, weights=parent.progWeights)[0]
                progIdx = parent.progLookup[progSetName]
                # choose an amplitude
                amplitudeMultiplier = random.choice(parent.stimAmpMultipliers)
                amplitudes = [0,0,0,0]
                amplitudes[progIdx] = amplitudeMultiplier * parent.stimMotorThreshold[progIdx]
                # if progSetName == 'midline':
                #     expectedMovementDuration = expectedMovementDuration * 2
                parent.summit.stimOneMovement(amplitudes, expectedMovementDuration - self.waitAtPeak / 2, frequency)
                sleepFor = parent.summit.transmissionDelay + 1 / frequency
                if sleepFor > 0:
                    time.sleep(sleepFor)
            if not parent.phantomMotor:
                if direction == 'forward':
                    parent.motor.forward()
                    if parent.dummyMotor:
                        parent.dummyMotor.forward()
                else:
                    parent.motor.backward()
                    if parent.dummyMotor:
                        parent.dummyMotor.backward()
                waitUntilDoneMoving(parent.motor)
            else:
                if expectedMovementDuration > 0:
                    print('Phantom motor; sleeping for {} sec'.format(expectedMovementDuration))
                    time.sleep(expectedMovementDuration)
            print('Sleeping until return ')
            if self.waitAtPeak - sleepFor > 0:
                time.sleep(self.waitAtPeak - sleepFor)
            # return phase of first movement
            # if parent.summit and progSetName in ['rostral', 'caudal']:
            #     amplitudes = [0,0,0,0]
            #     altProgSetName = 'rostral' if progSetName == 'caudal' else 'caudal'
            #     altProgIdx = parent.progLookup[altProgSetName]
            #     amplitudes[altProgIdx] = amplitudeMultiplier * parent.stimMotorThreshold[altProgIdx]
            if parent.summit:
                # choose an electrode for this stim
                progSetName = random.choices(parent.progNames, weights=parent.progWeights)[0]
                progIdx = parent.progLookup[progSetName]
                # choose an amplitude
                amplitudeMultiplier = random.choice(parent.stimAmpMultipliers)
                amplitudes = [0,0,0,0]
                amplitudes[progIdx] = amplitudeMultiplier * parent.stimMotorThreshold[progIdx]
                parent.summit.stimOneMovement(amplitudes, expectedMovementDuration - self.waitAtPeak / 2, frequency)
                if parent.summit.transmissionDelay > 0:
                    time.sleep(parent.summit.transmissionDelay + 1 / frequency)
            if not parent.phantomMotor:
                parent.motor.go_home()
                if parent.dummyMotor:
                    parent.dummyMotor.go_home()
                waitUntilDoneMoving(parent.motor)
            else:
                if expectedMovementDuration > 0:
                    print('Phantom motor; sleeping for {} sec'.format(expectedMovementDuration))
                    time.sleep(expectedMovementDuration)
            return

        self.payload = {
            "Stimulus ID Pair": magnitudeIndex,
            'firstThrow': random.gauss(
                parent.movementMagnitudes[magnitudeIndex[0]], self.angleJitter),
            'secondThrow' : random.gauss(
                parent.movementMagnitudes[magnitudeIndex[1]], self.angleJitter),
            'movementOnset' : time.time(),
            'movementOff' : 0, 'vibrationOn' : False}
            
        #play movement division tone
        executeMovement(self.payload['firstThrow'])
        parent.magnitudeQueue.append(parent.motor.step_size)
        parent.speaker.play_tone('Divider')
        #wait between movements
        time.sleep( 3 * self.waitAtPeak)
        executeMovement(self.payload['secondThrow'])

        self.payload['movementOff'] = time.time()
        parent.magnitudeQueue.append(parent.motor.step_size)

        #Obviate the need to stop by the set_correct state
        parent.correctButton = 'left' if parent.magnitudeQueue[0] < parent.magnitudeQueue[1] else 'right'
        if direction == 'backward':
            self.payload['firstThrow'] *= -1
            self.payload['secondThrow'] *= -1
        # empty event queue and start monitoring for aberrant button presses
        if parent.inputPin.last_data is not None:
            parent.inputPin.last_data = None

        if self.printStatements:
            print('  ')
            print('Correct button set to: %s' % parent.correctButton)
        parent.magnitudeQueue = []

        if parent.motor.useEncoder:
            curPos = parent.motor.get_encoder_position()

        event_label = parent.request_last_touch()
        if event_label and self.timePenalty:
            parent.speaker.play_tone('Wait')
            sleepTime = 0.05
        else:
            sleepTime = 0

        while sleepTime > 0:
            # Read from inbox
            time.sleep(0.05)
            sleepTime = sleepTime - 0.05
            event_label = parent.request_last_touch()
            if event_label and self.timePenalty:
                # if erroneous button press, play bad tone, and penalize with an extra
                # timePenalty millisecond wait
                parent.speaker.play_tone('Wait')
                sleepTime = sleepTime + self.timePenalty
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
        #print('Trial Started!')
        return self.nextState[0]

class chooseReportDifficulty(gameState):
    def __init__(
            self, nextState, parent, stateName,
            logFile=None, printStatements=False,
            probaBins=None):
        super().__init__(
            nextState, parent, stateName,
            logFile=logFile, printStatements=printStatements)
        self.probaBins = probaBins
        
    def operation(self, parent):
        draw = random.random()
        return self.nextState[int(np.digitize(draw, self.probaBins) - 1)]

class set_correct(gameState):

    def operation(self, parent):
        parent.correctButton = 'left'\
            if parent.magnitudeQueue[0] < parent.magnitudeQueue[1]\
            else 'right'

        if self.printStatements:
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

            if self.printStatements:
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

            if self.printStatements:
                print('Started Timed Button')
            # Turn LED's On
            parent.outbox.put('leftLED')
            parent.outbox.put('rightLED')

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

            if self.printStatements:
                print("\n%s button pressed!" % event_label)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('leftLED')
            parent.outbox.put('rightLED')
            if self.printStatements:
                print(' ')
            return self.nextState[0] # usually the good state

        if self.timedOut:
            if self.logFile:
                self.logFile.write("\nbutton timed out\t %4.4f\t" % self.timeNow)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('leftLED')
            parent.outbox.put('rightLED')

            if self.printStatements:
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
            if self.printStatements:
                print('Started Timed Button')

            self.logEvent('goEasy', None)
            #obviate the need to stop by trial_start
            parent.speaker.play_tone('Go')
            # Turn LED's On
            parent.outbox.put('leftLED' if parent.correctButton == 'left' else 'rightLED')

            self.firstVisit = False
            self.enableLog = False

            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.responseWindow

            if parent.cuedRewardDur is not None:
                parent.juicePin.instructions =\
                    ['flip', 'flip', 'flip', ('pulse', parent.cuedRewardDur)]
            if (parent.cuedJackpotRewardDur is not None) and (parent.jackpot):
                    parent.juicePin.instructions =\
                        ['flip', 'flip', 'flip', ('pulse', parent.cuedJackpotRewardDur)]
        # Read from inbox
        event_label = parent.request_last_touch()

        self.checkTimedOut()

        if event_label:
            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('leftLED' if parent.correctButton == 'left' else 'rightLED')

            if self.printStatements:
                print(' ')

            if event_label == 'right':
                parent.rightTally = parent.rightTally * 0.7 + 1
                parent.leftTally = parent.leftTally * 0.7
            elif  event_label == 'left':
                parent.leftTally = parent.leftTally * 0.7 + 1
                parent.rightTally = parent.rightTally * 0.7

            if event_label == parent.correctButton:
                if self.logFile:
                    #TODO: replace all these with calls to logEvent
                    self.logEvent('correct button', event_label)

                if self.printStatements:
                    print("\n%s button pressed correctly!" % event_label)
                return self.nextState[0] # usually the good state
            else:
                if self.logFile:
                    self.logEvent('incorrect button', event_label)
                if self.printStatements:
                    print("\n%s button pressed incorrectly!" % event_label)
                return self.nextState[1] # usually the good state

        if self.timedOut:
            if self.logFile:
                self.logEvent('button timed out', None)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            parent.outbox.put('leftLED' if parent.correctButton == 'left' else 'rightLED')

            if self.printStatements:
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
    def __init__(
            self, nextState, parent, stateName,
            logFile=None, printStatements=False,
            lighting=True):
        super().__init__(
            nextState, parent, stateName,
            logFile=logFile, printStatements=printStatements)
        self.lighting = lighting

    def operation(self, parent):
        if self.firstVisit:
            if self.printStatements:
                print('Started Timed Button Uncued')
            self.logEvent('goHard', None)
            #obviate the need to stop by trial_start
            parent.speaker.play_tone('Go')
            # Turn LED's On
            if self.lighting:
                parent.outbox.put('bothLED')

            self.firstVisit = False
            self.enableLog = False

            self.timeNow = time.time()
            self.nextTimeOut = self.timeNow + parent.responseWindow

            if parent.uncuedRewardDur is not None:
                parent.juicePin.instructions =\
                    ['flip', 'flip', 'flip', ('pulse', parent.uncuedRewardDur)]
            if (parent.uncuedJackpotRewardDur is not None) and (parent.jackpot):
                parent.juicePin.instructions =\
                    ['flip', 'flip', 'flip', ('pulse', parent.uncuedJackpotRewardDur)]

        # Read from inbox
        event_label = parent.request_last_touch()

        self.checkTimedOut()

        if event_label:

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False

            if self.lighting:
                parent.outbox.put('bothLED')

            if self.printStatements:
                print(' ')

            if event_label == 'left':
                parent.leftTally = 0.7 * parent.leftTally + 1
                parent.rightTally = 0.7 * parent.rightTally
            elif  event_label == 'right':
                parent.leftTally = 0.7 * parent.leftTally
                parent.rightTally = 0.7 * parent.rightTally + 1

            if event_label == parent.correctButton:
                if self.logFile:
                    self.logEvent('correct button', event_label)
                if self.printStatements:
                    print("\n%s button pressed correctly!" % event_label)
                return self.nextState[0] # usually the good state
            else:
                if self.logFile:
                    self.logEvent('incorrect button', event_label)

                if self.printStatements:
                    print("\n%s button pressed incorrectly!" % event_label)
                return self.nextState[1] # usually the good state

        if self.timedOut:
            if self.logFile:
                self.logEvent('button timed out', None)

            #leaving wait_for_button, turn logging on for next return to this state
            self.enableLog = True
            self.firstVisit = True
            self.timedOut = False
            if self.lighting:
                parent.outbox.put('bothLED')

            if self.printStatements:
                print(' ')
            # re enable logging for future visits
            return self.nextState[1] # usually the post-trial state

        else: # if not parent.buttonTimedOut
            time.sleep(self.sleepTime)

            if self.printStatements:
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
            if self.printStatements:
                print("\n%s button pressed!" % event_label)

            nextFun = self.nextState[0] if parent.correctButton == event_label else self.nextState[1]

            self.firstVisit = True
            self.enableLog = True
            return nextFun
        else:
            time.sleep(self.sleepTime)
            if self.printStatements:
                sys.stdout.write("Waiting for button...\r")
                sys.stdout.flush()
            return 'wait_for_correct_button'

class good(gameState):
    # TODO: add amount dispensed to log
    def operation(self, parent):
        if self.printStatements:
            print('Good job!')
        parent.fixationDuration = parent.nominalFixationDur
        parent.outbox.put('Reward')
        parent.speaker.play_tone('Good')
        return self.nextState[0]

class stochasticGood(gameState):
    def __init__(
            self, nextState, parent, stateName,
            logFile=None, printStatements=False,
            threshold=None):
        super().__init__(
            nextState, parent, stateName,
            logFile=logFile, printStatements=printStatements)
        self.threshold = threshold
    # TODO: add amount dispensed to log
    def operation(self, parent):
        if self.printStatements:
            print('Good job!')
            if parent.jackpot:
                print('JACKPOT!')
        parent.fixationDur = parent.nominalFixationDur
        if random.uniform(0,1) > self.threshold:
            parent.outbox.put('Reward')
        parent.speaker.play_tone('Good')
        return self.nextState[0]

class bad(gameState):

    def operation(self, parent):
        if self.printStatements:
            print('Wrong! Try again!')
        parent.fixationDur = parent.nominalFixationDur + parent.wrongTimeout
        parent.speaker.play_tone('Bad')
        return self.nextState[0]

class post_trial(gameState):

    def operation(self, parent):
        print('At post trial')
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
