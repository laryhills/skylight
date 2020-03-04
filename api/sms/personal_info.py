from flask import abort
from sms.config import db
from sms import utils
from sms.models.master import Master, MasterSchema
from sms.users import access_decorator

@access_decorator
def get(mat_no, ret_JSON=True, req_perms=["read"]):
    db_name = utils.get_DB(mat_no)[:-3]
    session = utils.load_session(db_name)
    PersonalInfo = session.PersonalInfo
    PersonalInfoSchema = session.PersonalInfoSchema
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first_or_404()
    personalinfo_schema = PersonalInfoSchema()
    if ret_JSON:
        return personalinfo_schema.dumps(student_data)
    return personalinfo_schema.dump(student_data)


@access_decorator
def post(student_data, req_perms=["write"]):
    global PersonalInfo, PersonalInfoSchema

    # todo: Get "session_admitted" from "current_session" in master.db for 100l
    # todo: On opening the personal info tab, the backend should supply this data
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
