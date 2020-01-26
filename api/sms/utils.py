from sys import modules
from sms.config import db
from importlib import reload
from sms import personal_info
from sms.models.master import Master, MasterSchema

'''
Handle frequently called or single use simple utility functions
These aren't exposed endpoints and needn't return json data
'''

lastLoaded = None


def getDB(mat_no):
    # Lookup the student's details in the master db
    student = Master.query.filter_by(mat_no=mat_no).first_or_404()
    master_schema = MasterSchema()
    db_name = master_schema.dump(student)['database']
    return db_name.replace('-', '_')


def getCredits(mat_no, mode_of_entry=None):
    db_name = getDB(mat_no)[:-3]
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    exec('from sms.models import _{}'.format(db_name))
    if ('sms.models._{}'.format(db_name) in modules) and (lastLoaded!=db_name):
        exec('reload(_{})'.format(db_name))
    lastLoaded = db_name

    Credits = eval('_{}.Credits'.format(db_name))
    CreditsSchema = eval('_{}.CreditsSchema'.format(db_name))

    if not mode_of_entry:
        person = loads(personal_info.get(mat_no=mat_no))
        mode_of_entry = person['mode_of_entry']
    
    credits = CreditsSchema().dump(Credits.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_credits = [credits['level{}'.format(lvl)] for lvl in range(mode_of_entry*100,600,100)]
    return level_credits


def getCourses(mat_no, mode_of_entry=None):
    db_name = getDB(mat_no)[:-3]
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    exec('from sms.models import _{}'.format(db_name))
    if ('sms.models._{}'.format(db_name) in modules) and (lastLoaded!=db_name):
        exec('reload(_{})'.format(db_name))
    lastLoaded = db_name

    Courses = eval('_{}.Courses'.format(db_name))
    CoursesSchema = eval('_{}.CoursesSchema'.format(db_name))

    if not mode_of_entry:
        person = loads(personal_info.get(mat_no=mat_no))
        mode_of_entry = person['mode_of_entry']
    
    courses = CoursesSchema().dump(Courses.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_courses = [courses['level{}'.format(lvl)] for lvl in range(mode_of_entry*100,600,100)]
    return level_courses
