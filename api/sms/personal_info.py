from sms import utils
from sms.config import db
from sms.models.master import Master, MasterSchema

all_fields = {'date_of_birth', 'email_address', 'grad_stats', 'level', 'lga', 'mat_no', 'mode_of_entry', 'othernames', 'phone_no', 'session_admitted', 'session_grad', 'sex', 'sponsor_email_address', 'sponsor_phone_no', 'state_of_origin', 'surname'}
required = all_fields - {'grad_stats', 'session_grad'}

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
    record_update = bool(utils.get_DB(data.get("mat_no")))
    
    if record_update:
        if not all([data.get(prop) for prop in (required & data.keys())]) or (data.keys() - all_fields):
            # Empty value supplied or Invalid field supplied
            return "Invalid field supplied"
    else:
        if not all([data.get(prop) for prop in required]) or (data.keys() - all_fields):
            # Empty value supplied or Invalid field supplied or Missing field present
            return "Invalid field supplied or missing a compulsory field"

    session_admitted = data['session_admitted']

    master_schema = MasterSchema()
    database = "{}-{}.db".format(session_admitted, session_admitted + 1)
    master_model = master_schema.load({'mat_no': data['mat_no'], 'database': database})

    db_name = "{}_{}".format(session_admitted, session_admitted + 1)
    session = utils.load_session(db_name)
    personalinfo_schema = session.PersonalInfoSchema()
    student_model = personalinfo_schema.load(data)
    student_model.is_symlink = 0

    db.session.add(master_model)
    db.session.commit()

    db_session = personalinfo_schema.Meta.sqla_session
    db_session.add(student_model)
    db_session.commit()
