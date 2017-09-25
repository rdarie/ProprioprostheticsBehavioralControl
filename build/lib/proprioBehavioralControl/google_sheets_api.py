from helperFunctions import get_gsheets_credentials, update_training_log
import time
values = [
    [time.strftime("%m/%d/%Y"), 'Button Pressing', '', '', '']
    ]

spreadsheetId = '1BWjBqbtoVr9j6dU_7eHp-bQMJApNn8Wkl_N1jv20faE'

update_training_log(spreadsheetId, values)
