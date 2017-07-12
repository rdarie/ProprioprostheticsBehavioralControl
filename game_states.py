import sys, random, time, pdb, shutil
from helperFunctions import overRideAdder

enableLog = True
firstVisit = True

class gameState(object):
    def __init__(self, nextState, parent, stateName, logFile = None):
        self.nextState = nextState
        self.logFile = logFile
        self.parent = parent
        self.__name__ = stateName

    def operation(self, parent):
        pass

    def __call__(self, *args):
        global enableLog
        if self.logFile:
            if enableLog:
                timeNow = time.time()
                self.logFile.write("\n%s\t%4.4f" % ( self.__name__, timeNow))

        if self.parent.remoteOverride is None:
            #print("in Python: Override is none! I am %s" % self.__name__)
            ret = self.operation(self.parent)
        else:
            #print("in Python: Override is NOT none! I am %s" % self.__name__)
            ret = self.parent.remoteOverride
            enableLog = True
            self.parent.remoteOverride = None
        #print("returning %s" % ret)
        return ret

class fixation(gameState):

    def operation(self, parent):
        global enableLog, firstVisit
        enableLog = False

        timeNow = time.time()


        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (parent.nextEnableTime - timeNow))
        sys.stdout.flush()

        time.sleep(0.5)

        if parent.nextEnableTime < timeNow:
            parent.startEnable = True

        if parent.startEnable:
            enableLog = True
            firstVisit = True
            return self.nextState[0]
        else:
            return self.nextState[1]

class turnPedal(gameState):

    def operation(self, parent):
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
        global enableLog
        enableLog = False
        # Read from inbox
        event_label = parent.request_last_touch()
        parent.startEnable = False

        if event_label:
            if self.logFile:
                self.logFile.write("\ncorrect_button\t%s\t" % event_label)
            print("\n%s button pressed!" % event_label)
            enableLog = True
            return self.nextState[0]
        else:
            time.sleep(0.1)

            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()

            return 'wait_for_any_button'

class wait_for_any_button_timed(gameState):
    def operation(self, parent):
        global enableLog, firstVisit
        enableLog = False
        #disable logging for subsequent visits to this state, until we leave it

        # Read from inbox
        event_label = parent.request_last_touch()
        parent.startEnable = False

        timeNow = time.time()
        if not firstVisit:
            if parent.nextButtonTimeout < timeNow:
                parent.buttonTimedOut = True

        if event_label:
            if self.logFile:
                self.logFile.write("\ncorrect_button\t%4.4f\t%s" % (timeNow, event_label))
            print("\n%s button pressed!" % event_label)

            enableLog = True
            parent.buttonTimedOut = False
            # re enable logging for future visits

            return self.nextState[0]
        if parent.buttonTimedOut:
            if self.logFile:
                self.logFile.write("\nbutton timed out!\t %4.4f\t" % timeNow)

            enableLog = True
            parent.buttonTimedOut = False
            # re enable logging for future visits
            return self.nextState[1]
        else:

            time.sleep(0.1)

            if firstVisit:
                firstVisit = False
                parent.nextButtonTimeout = timeNow + parent.trialLimit

            sys.stdout.write("Waiting for button... Time left: %4.4f \r" %
                (parent.nextButtonTimeout - timeNow))
            sys.stdout.flush()

            return 'wait_for_any_button_timed'


class wait_for_correct_button(gameState):
    def operation(self, parent):
        # Read from inbox
        event_label = parent.request_last_touch()
        parent.startEnable = False

        if event_label:
            if self.logFile:
                self.logFile.write("\nbutton_pressed\t%s\t" % event_label)
            print("\n%s button pressed!" % event_label)
            nextFun = self.nextState[0] if parent.correctButton == event_label else self.nextState[1]
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
        return self.nextState[0]

class end(gameState):

    def operation(self, parent):

        print('@game_states.py, end')
        src = parent.logFileName
        dst = parent.serverFolder + '/' + parent.logFileName.split('/')[-1]
        shutil.move(src,dst)
        scriptPath = '/home/pi/research/Data-Analysis/evaluatePerformance.py'

        subprocess.check_output('python3 ' + scriptPath + ' --file '  + '\"' +
            parent.logFileName.split('/')[-1] + '\"' + ' --folder \"' +
            dst + '\"', shell=True)
        return self.nextState[0]
