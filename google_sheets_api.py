from helperFunctions import get_gsheets_credentials, update_training_log
import time
values = [
    [time.strftime("%m/%d/%Y"), 'Button Pressing', '', '', '']
    ]
update_training_log(values)
