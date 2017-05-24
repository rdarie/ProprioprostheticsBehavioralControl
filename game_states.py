import sys, random, time, pdb

def fixation_constructor(nextState = ['set_correct',  'fixation']):
    def fixation(self):
        timeNow = time.time()
        sys.stdout.write("At fixation. Time left: %4.4f \r"
         % (self.nextEnableTime - timeNow))
        sys.stdout.flush()
        time.sleep(0.5)

        if self.nextEnableTime < timeNow:
            self.startEnable = True

        if self.startEnable:
            return nextState[0]
        else:
            return nextState[1]
    return fixation

def turnPedal_constructor(nextState = ['set_correct']):
    def turnPedal(self):
        return nextState[0]
    return turnPedal

def clear_input_queue_constructor(nextState = ['wait_for_any_button']):
    def clear_input_queue(self):
        # clear the button inputs queue
        # TODO: Make this thread safe
        if self.inputPin.last_data is not None:
            self.inputPin.last_data = None
        return nextState[0]
    return clear_input_queue

def trial_start_constructor(nextState = ['clear_input_queue']):
    def trial_start(self):
        self.speaker.play_tone('Go')
        print('Trial Started!')
        return nextState[0]
    return trial_start

def set_correct_constructor(nextState = ['trial_start']):
    def set_correct(self):
        self.correctButton = 'red' if random.randint(0,1) == 0 else 'blue'
        print('  ')
        print('Correct button set to: %s' % self.correctButton)

        return nextState[0]
    return set_correct

def wait_for_any_button_constructor(nextState = ['good']):
    def wait_for_any_button(self):
        # Read from inbox
        event_label = self.request_last_touch()
        self.startEnable = False

        if event_label:
            print("\n%s button pressed!" % event_label)
            return nextState[0]
        else:
            time.sleep(0.1)
            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()
            return 'wait_for_any_button'
    return wait_for_any_button

def wait_for_correct_button_constructor(nextState = ['good', 'bad']):
    def wait_for_correct_button(self):
        # Read from inbox
        event_label = self.request_last_touch()
        self.startEnable = False

        if event_label:
            print("\n%s button pressed!" % event_label)
            nextFun = nextState[0] if self.correctButton == event_label else nextState[1]
            return nextFun
        else:
            time.sleep(0.01)
            sys.stdout.write("Waiting for button...\r")
            sys.stdout.flush()
            return 'wait_for_correct_button'
    return wait_for_correct_button

def good_constructor(nextState = ['post_trial']):
    def good(self):
        print('Good job!')
        self.speaker.play_tone('Good')
        return nextState[0]
    return good

def bad_constructor(nextState = ['post_trial']):
    def bad(self):
        print('Wrong! Try again!')
        self.speaker.play_tone('Bad')
        return nextState[0]
    return bad

def post_trial_constructor(nextState = ['fixation']):
    def post_trial(self):
        self.nextEnableTime = time.time() + self.trialLength
        return nextState[0]
    return post_trial

def end_constructor(nextState = [False]):
    def end(self):
        print('Ending now')
        return nextState[0]
    return end
