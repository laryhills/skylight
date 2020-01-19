from sys import modules
from flask import abort
from sms.config import db
from sms import master_poll
from importlib import reload
from sms.models.master import Master, MasterSchema

lastLoaded = None

def get(mat_no):
    #Get db file for student
    db_name = master_poll.getDB(mat_no)[:-3]
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    if ('sms.models._{}'.format(db_name) in modules) and (lastLoaded!=db_name):
        exec('from sms.models import _{}'.format(db_name))
        exec('reload(_{})'.format(db_name))
        lastLoaded = db_name
    else:
        exec('from sms.models import _{}'.format(db_name))
        lastLoaded = db_name
    #Get PersonalInfo
    PersonalInfo = eval('_{}.PersonalInfo'.format(db_name))
    PersonalInfoSchema = eval('_{}.PersonalInfoSchema'.format(db_name))
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first_or_404()
    personalinfo_schema = PersonalInfoSchema()
    return personalinfo_schema.dumps(student_data)

def post(student_data):
    global PersonalInfo, PersonalInfoSchema
    session = int(student_data['session_admitted'])
    db_name = '{}_{}.db'.format(session, session + 1)

    try:
        exec('from sms.models._{} import PersonalInfoSchema'.format(db_name[:-3]))
    except ImportError:
        # create and import new database model
        abort(400)
    db_name = db_name.replace('_', '-')
    master_schema = MasterSchema()
    master_model = master_schema.load({'mat_no': student_data['mat_no'], 'database': db_name})
    PersonalInfoSchema = locals()['PersonalInfoSchema']
    personalinfo_schema = PersonalInfoSchema()
    student = personalinfo_schema.load(student_data)
    student.is_symlink = 0
    db.session.add(master_model)
    db.session.add(student)
    db.session.commit()
