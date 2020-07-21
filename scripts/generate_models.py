import os

models_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'models')
base_dir = os.path.dirname(__file__)

sessions = range(2003, 2020)
for session in sessions:
    model = open(os.path.join(models_dir, '_{0}_{1}.py'.format(session, session + 1)), 'w')
    temp_file_path = os.path.join(base_dir, 'model_template.txt')
    temp_file = open(temp_file_path)
    lines = temp_file.readlines()
    for index in range(len(lines)):
        lines[index] = lines[index].replace(
            '##NAME##', '{0}-{1}'.format(session, session + 1)).replace(
            '##NAME_2##', '_{0}_{1}'.format(session, session + 1))
    model.writelines(lines)

print('Done')
