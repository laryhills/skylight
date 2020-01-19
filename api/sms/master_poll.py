from sms.config import db
from sms.models.master import Master, MasterSchema

def getDB(mat_no):
    # Lookup the student's details in the master db
    student = Master.query.filter_by(mat_no=mat_no).first_or_404()
    master_schema = MasterSchema()
    db_name = master_schema.dump(student)['database']
    return db_name.replace('-', '_')
