import os

separator = os.path.sep
curr_path = os.path.abspath(__file__)
project_root = separator.join(curr_path.split(separator)[:-3])

db_base_dir = os.path.join(project_root, 'sms', 'database')
models_dir = os.path.join(project_root, 'sms', 'models')
model_template_path = os.path.join(project_root, 'setup', 'src', 'common', 'model_template.txt')
