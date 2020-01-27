from json import loads, dumps
from sys import modules
from sms.config import db
from importlib import reload
from sms import personal_info
from sms import result_statement
from sms import course_details
from sms.models.master import Master, MasterSchema
from sms.models.courses import Options, OptionsSchema

'''
Handle frequently called or single use simple utility functions
These aren't exposed endpoints and needn't return json data (exc get_carryovers)
'''

lastLoaded = None


def get_DB(mat_no):
    # Lookup the student's details in the master db
    student = Master.query.filter_by(mat_no=mat_no).first_or_404()
    master_schema = MasterSchema()
    db_name = master_schema.dump(student)['database']
    return db_name.replace('-', '_')


def get_credits(mat_no, mode_of_entry=None):
    db_name = get_DB(mat_no)[:-3]
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


def get_courses(mat_no, mode_of_entry=None):
    db_name = get_DB(mat_no)[:-3]
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
    
    level_courses = []
    for lvl in range(100,600,100):
        course_string = courses['level{}'.format(lvl)]
        if course_string:
            first_sem, second_sem = course_string.split()
            level_courses.append([first_sem.split(','),second_sem.split(',')])
        else:
            level_courses.append(None)
    return level_courses


def get_carryovers(mat_no, level=None):
    level = int(level/100) if level else None
    first_sem = [set(x[0]) for x in get_courses(mat_no)[:level] if x]
    second_sem = [set(x[1]) for x in get_courses(mat_no)[:level] if x]
    results = loads(result_statement.get(mat_no))["results"][:level]

    options = {}
    for option in Options.query.all():
        option=OptionsSchema().dump(option)
        options[option['options_group']] = {'members': option['members'],
                                            'default_member': option['default_member']}

    for result in results:
        for record in result["first_sem"]:
            (course, credit, grade) = (record[1], record[3], record[5])

            option = loads(course_details.get(course))["options"]
            if option:
                def_course = options[option]["default_member"]
                if course != def_course:
                    if grade == "F":
                        for courses in first_sem:
                            if def_course in courses:
                                courses.remove(def_course)
                                courses.add(course)
                                break
                    else:
                        for courses in first_sem:
                            if def_course in courses:
                                courses.remove(def_course)
                                break
            if grade != "F":
                for courses in first_sem:
                    if course in courses:
                        courses.remove(course)

        for record in result["second_sem"]:
            (course, credit, grade) = (record[1], record[3], record[5])

            option = loads(course_details.get(course))["options"]
            if option:
                def_course = options[option]["default_member"]
                if course != def_course:
                    if grade == "F":
                        for courses in second_sem:
                            if def_course in courses:
                                courses.remove(def_course)
                                courses.add(course)
                                break
                    else:
                        for courses in second_sem:
                            if def_course in courses:
                                courses.remove(def_course)
                                break
            if grade != "F":
                for courses in second_sem:
                    if course in courses:
                        courses.remove(course)

    carryovers = {"first_sem":[],"second_sem":[]}
    for lvl_co in first_sem:
        for failed_course in lvl_co:
            credit = loads(course_details.get(failed_course))["course_credit"]
            carryovers["first_sem"].append([failed_course, str(credit)])
    for lvl_co in second_sem:
        for failed_course in lvl_co:
            credit = loads(course_details.get(failed_course))["course_credit"]
            carryovers["second_sem"].append([failed_course, str(credit)])
    return dumps(carryovers)
