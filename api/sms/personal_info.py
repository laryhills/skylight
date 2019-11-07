from flask import abort
from sms.config import db
from sms.models.master import Master, MasterSchema

PersonalInfo = None
PersonalInfoSchema = None


def get(mat_no=None):
    global PersonalInfo, PersonalInfoSchema
    if mat_no:
        # Lookup the student's details in the master db
        student = Master.query.filter_by(mat_no=mat_no).first_or_404()
        master_schema = MasterSchema()
        db_name = master_schema.dump(student)['database']
        db_name = db_name.replace('-', '_')

        # Gets the student's details
        exec('from sms.models._{} import PersonalInfo, PersonalInfoSchema'.format(db_name[:-3]))
        PersonalInfo = locals()['PersonalInfo']
        PersonalInfoSchema = locals()['PersonalInfoSchema']
        student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first_or_404()
        personalinfo_schema = PersonalInfoSchema()

        return personalinfo_schema.dumps(student_data)

    abort(400)


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
