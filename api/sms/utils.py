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


def load_session(session):
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    exec('from sms.models import _{}'.format(session))
    if ('sms.models._{}'.format(session) in modules) and (lastLoaded!=session):
        exec('reload(_{})'.format(session))
    lastLoaded = session
    return eval('_{}'.format(session))


def get_current_session():
    # Code stub that returns current session, TODO take from master.db
    return 2019


def get_level(mat_no, next = False):
    # 0 - do estimate level; 600 - is graduate, 100-500 spill inc
    # if next = True, return next level else current level
    curr_level = personal_info.get(mat_no, 0)['current_level']
    result_stmt = result_statement.get(mat_no, 0)
    results = result_stmt["results"]
    if curr_level and not results:
        # current level on record, if no result - be optimistic on moving to next level
        print ("WARNING: No result record for", mat_no, "using stored level record")
        if not next:
            return curr_level
        return curr_level + 100
    if curr_level == 0:
        if not results:
            print ("No result for", mat_no, "can't det level")
            return 0
        else:
            # No level record, use highest courses written to estimate
            last_result = results[-1]["first_sem"] + results[-1]["second_sem"]
            course_levels = [course_details.get(code, 0)["course_level"]
                             for lvl, code, title, weight, score, grade in last_result]
            curr_level = max(course_levels)
    # current level presently determined, if next determine using results
    if next:
        if curr_level >= 500:
            inc_level = [0, 100][result_stmt["category"][-1] in ('A')]
        else:
            inc_level = [0, 100][result_stmt["category"][-1] in ('A', 'B')]
        return curr_level + inc_level
    return curr_level


def get_credits(mat_no, mode_of_entry=None):
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    Credits, CreditsSchema = session.Credits, session.CreditsSchema

    if not mode_of_entry:
        person = loads(personal_info.get(mat_no=mat_no))
        mode_of_entry = person['mode_of_entry']
    
    credits = CreditsSchema().dump(Credits.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_credits = [credits['level{}'.format(lvl)] for lvl in range(mode_of_entry*100,600,100)]
    return level_credits


def get_courses(mat_no, mode_of_entry=None):
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    Courses, CoursesSchema = session.Courses, session.CoursesSchema

    if not mode_of_entry:
        person = loads(personal_info.get(mat_no=mat_no))
        mode_of_entry = person['mode_of_entry']
    
    courses = CoursesSchema().dump(Courses.query.filter_by(mode_of_entry=mode_of_entry).first())
    
    level_courses = []
    for lvl in range(100,600,100):
        course_string = courses['level{}'.format(lvl)]
        if course_string:
            if len(course_string.split()) == 1:
                #Handle abscence of UBITS / sec sem
                first_sem = course_string.split()[0]
                level_courses.append([first_sem.split(','),[]])
            else:
                first_sem, second_sem = course_string.split()
                level_courses.append([first_sem.split(','),second_sem.split(',')])
        else:
            level_courses.append(None)
    return level_courses


def get_carryovers(mat_no, retJSON=True):
    level = get_level(mat_no)
    first_sem, second_sem = set(), set()
    results = loads(result_statement.get(mat_no))["results"]
    for course in get_courses(mat_no)[:int(level/100)]:
        first_sem |= set(course[0] if course else set())
        second_sem |= set(course[1] if course else set())

    person = loads(personal_info.get(mat_no))
    person_option = person['option'].split(',') if person['option'] else None
    if person_option:
        # Put in option if registered
        options = []
        for option in Options.query.all():
            option=OptionsSchema().dump(option)
            options.append({'members': option['members'],
                            'group': option['options_group'],
                            'default': option['default_member']})

        for opt in person_option:
            for option in options:
                if opt in option["members"].split(','):
                    default = option["default"]
                    sem = course_details.get(default,0)["course_semester"]
                    if default != opt:
                        [first_sem, second_sem][sem-1].remove(default)
                        [first_sem, second_sem][sem-1].add(opt)

    for result in results:
        for record in result["first_sem"]:
            (course, credit, grade) = (record[1], record[3], record[5])
            if grade not in ("F", "ABS"):
                if course in first_sem:
                    first_sem.remove(course)

        for record in result["second_sem"]:
            (course, credit, grade) = (record[1], record[3], record[5])
            if grade not in ("F", "ABS"):
                if course in second_sem:
                    second_sem.remove(course)

    if level == get_level(mat_no,1) and level in (200, 300, 400):
        # Handle probation carryovers
        print ("Probating {} student".format(level))
        first_sem |= set(get_courses(mat_no)[int(level/100)-1][0])
        second_sem |= set(get_courses(mat_no)[int(level/100)-1][1])

    carryovers = {"first_sem":[],"second_sem":[]}
    for failed_course in first_sem:
        credit = loads(course_details.get(failed_course))["course_credit"]
        carryovers["first_sem"].append([failed_course, str(credit)])
    for failed_course in second_sem:
        credit = loads(course_details.get(failed_course))["course_credit"]
        carryovers["second_sem"].append([failed_course, str(credit)])
    if retJSON:
        return dumps(carryovers)
    return carryovers


def result_poll(mat_no, level=None):
    #Get result for all levels if level=None else for level
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    ans=[]
    levels = [level] if level else range(100,900,100)
    for level in levels:
        resLvl = eval('session.Result{}.query.filter_by(mat_no=mat_no).first()'.format(level))
        resStr = eval('session.Result{}Schema().dump(resLvl)'.format(level))
        ans.append(resStr)
    return ans


def get_registered_courses(mat_no, level=None):
    # Get courses registered for all levels if level=None else for level
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    courses_registered=[]
    levels = range(100,900,100)
    for _level in levels:
        courses_regd = eval('session.CourseReg{}.query.filter_by(mat_no=mat_no).first()'.format(_level))
        courses_regd_str = eval('session.CourseReg{}Schema().dump(courses_regd)'.format(_level))
        if courses_regd_str != {}:
            courses_registered.append(courses_regd_str)
    if level:
        try:
            return courses_registered[(level//100)-1]
        except IndexError:
            return []
    return courses_registered
