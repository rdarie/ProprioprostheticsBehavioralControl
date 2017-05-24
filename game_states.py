import sys, random, time, pdb

def fixation(self):
    sys.stdout.write("At fixation...\r")
    sys.stdout.flush()

    if self.nextEnableTime < time.time():
        self.startEnable = True

    if self.startEnable:
        return 'turnPedal'
    else:
        return 'fixation'

def turnPedal(self, cargo=None):
    return 'set_correct'

def set_correct(self, cargo = None):
    self.correctButton = 'red' if random.randint(0,1) == 0 else 'blue'
    print('  ')
    print('Correct button set to: %s' % self.correctButton)
    return 'wait_for_button'

def wait_for_button(self, cargo=None):
    print('Trial Started! Waiting for button')

    self.speaker.play_tone('Go')
    # Read from inbox
    event_label = self.request_next_touch()
    self.startEnable = False

    print("%s button pressed!" % event_label[0])
    nextFun = 'good' if self.correctButton == event_label[0] else 'bad'
    return nextFun

def good(self, cargo=None):
    print('Good job!')
    self.speaker.play_tone('Good')
    return 'post_trial'

def bad(self, cargo=None):
    print('Wrong! Try again!')
    self.speaker.play_tone('Bad')
    return 'post_trial'

def post_trial(self, cargo = None):
    self.nextEnableTime = time.time() + self.trialLength
    return 'fixation'

def end(self, cargo=None):
    print('Ending now')
    return False
