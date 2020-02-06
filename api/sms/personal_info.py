from sys import modules
from flask import abort
from sms.config import db
from sms import utils
from importlib import reload
from sms.models.master import Master, MasterSchema

lastLoaded = None

def get(mat_no, retJSON=True):
    #Get db file for student
    db_name = utils.get_DB(mat_no)[:-3]
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    exec('from sms.models import _{}'.format(db_name))
    if ('sms.models._{}'.format(db_name) in modules) and (lastLoaded!=db_name):
        exec('reload(_{})'.format(db_name))
    lastLoaded = db_name
    #Get PersonalInfo
    PersonalInfo = eval('_{}.PersonalInfo'.format(db_name))
    PersonalInfoSchema = eval('_{}.PersonalInfoSchema'.format(db_name))
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first_or_404()
    personalinfo_schema = PersonalInfoSchema()
    if retJSON:
        return personalinfo_schema.dumps(student_data)
    return personalinfo_schema.dump(student_data)

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
