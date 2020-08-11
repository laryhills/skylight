import os

# declare project root path
separator = os.path.sep
base_dir = os.path.dirname(__file__)
project_root = separator.join(base_dir.split(separator)[:-2])

# declare other paths
model_template_path = os.path.join(project_root, 'setup', 'src', 'common', 'model_template.txt')
models_dir = os.path.join(project_root, 'sms', 'models')

sessions = range(2003, 2020)
for session in sessions:
    model = open(os.path.join(models_dir, '_{0}_{1}.py'.format(session, session + 1)), 'w')
    model_template = open(model_template_path)
    lines = model_template.readlines()
    for index in range(len(lines)):
        lines[index] = lines[index].replace(
            '##NAME##', '{0}-{1}'.format(session, session + 1)).replace(
            '##NAME_2##', '_{0}_{1}'.format(session, session + 1))
    model.writelines(lines)
    model.close()

print('Done')
