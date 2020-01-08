import os

models_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'models')
sessions = range(2003, 2018)
for session in sessions:
    model = open(os.path.join(models_dir, '_{0}_{1}.py'.format(session, session + 1)), 'w')
    temp_file = open('model_template.txt')
    lines = temp_file.readlines()
    for index in range(len(lines)):
        lines[index] = lines[index].replace('##NAME##', '{0}-{1}'.format(session, session + 1))
    model.writelines(lines)

print('Done')
