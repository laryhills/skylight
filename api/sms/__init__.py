import os
import shutil

generated_pdfs = {}

try:
    os.makedirs(os.path.join(os.path.expanduser('~'), 'sms', 'cache'))
except FileExistsError:
    shutil.rmtree(os.path.join(os.path.expanduser('~'), 'sms', 'cache'))
    os.mkdir(os.path.join(os.path.expanduser('~'), 'sms', 'cache'))
