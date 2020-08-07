from sms.config import db
from sms import utils
from sms.models.master import Master, MasterSchema

all_fields = {"date_of_birth", "email_address", "grad_stats", "level", "mat_no", "mode_of_entry", "othernames", "phone_no", "session_admitted", "sex", "sponsor_email_address", "sponsor_phone_no", "state_of_origin", "surname"}
required = {"session_admitted", "mat_no", "level", "mode_of_entry", "othernames", "surname", "sex"}

def get(mat_no):
    db_name = utils.get_DB(mat_no)
    if not db_name:
        return None
    session = utils.load_session(db_name)
    PersonalInfo = session.PersonalInfo
    PersonalInfoSchema = session.PersonalInfoSchema
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first()
    personalinfo_schema = PersonalInfoSchema()
    return personalinfo_schema.dump(student_data)


def post(data):
    # TODO add patch path for modifying properties

    if not all([data.get(prop) for prop in required]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied or Missing field present
        return "Invalid field supplied or missing a compulsory field", 400

    session_admitted = data['session_admitted']

    master_schema = MasterSchema()
    database = "{}-{}.db".format(session, session + 1)
    master_model = master_schema.load({'mat_no': data['mat_no'], 'database': database})

    db_name = "{}_{}".format(session, session + 1)
    session = utils.load_session(db_name)
    personalinfo_schema = session.PersonalInfoSchema()
    student_model = personalinfo_schema.load(data)
    student.is_symlink = 0

    db.session.add(master_model)
    db.session.add(student_model)
    db.session.commit()
