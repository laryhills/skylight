from collections import defaultdict
from json import loads, dumps
from sms import personal_info
from sms import result_statement
from sms import course_details
from sms import users
from sms import config
from sms.models.courses import Options, OptionsSchema
from sms.models.master import Category, Category500
from sqlalchemy.orm import class_mapper
import sqlalchemy.orm

'''
Handle frequently called or single use simple utility functions
These aren't exposed endpoints and needn't return json data (exc get_carryovers)
'''

get_DB = users.get_DB
get_level = users.get_level
load_session = users.load_session
get_current_session = config.get_current_session


def get_depat(form='long'):
    """
    Returns the name of the department as a string either in it's short or long form

    :param form: 'short' or 'long'
    :return: name of the department
    """
    if form == 'short':
        return 'MEE'
    return 'MECHANICAL ENGINEERING'


def get_credits(mat_no, mode_of_entry=None, session=None):
    """
    For a given `mat_no` and `mode_of_entry`, it returns a list of all the total credits for each level

    :param mat_no: mat number of student
    :param mode_of_entry: (Optional) mode of entry of student
    :param session:
    :return: list of total credits for each level
    """
    if not session:
        db_name = get_DB(mat_no)[:-3]
        session = load_session(db_name)
    Credits, CreditsSchema = session.Credits, session.CreditsSchema

    if not mode_of_entry:
        person = loads(personal_info.get(mat_no=mat_no))
        mode_of_entry = person['mode_of_entry']
    
    credits = CreditsSchema().dump(Credits.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_credits = [credits['level{}'.format(lvl)] for lvl in range(mode_of_entry*100,600,100)]
    return level_credits


def get_maximum_credits_for_course_reg():
    return {'normal': 50,
            'clause_of_51': 51}


def get_courses(mat_no, mode_of_entry=None):
    """
    Returns a list of all the courses that a student with given `mat_no` is eligible to write/register.

    Each item of the list is a list of all the level courses. Semester courses are separated in lists within
    a level course list.

    :param mat_no: mat number of student
    :param mode_of_entry: (Optional) mode of entry of student
    :return: list of courses
    """
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


def get_carryovers(mat_no, level=None, retJSON=True):
    """
    Returns a dictionary or JSON array of the carryovers for a student. Returns a JSON object if retJSON
    is true else a dictionary

    :param mat_no: mat number of student
    :param level: (Optional) level of the student
    :param retJSON: (Optional) if True returns a JSON array
    :return: Dictionary or JSON array of carryover courses
    """
    level = get_level(mat_no) if not level else level
    first_sem, second_sem = set(), set()
    results = loads(result_statement.get(mat_no))["results"]
    for course in get_courses(mat_no)[:int(level/100-1)]:
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

    results = [x for x in result_poll(mat_no) if x]
    if results and results[-1]["category"] == "C" and level in (200, 300, 400):
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
    """
    Get the results of a student

    Returns the result for all levels if `level` is None else for `level`

    :param mat_no: mat number of student
    :param level: level of the result
    :return: List of results
    """
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    ans=[]
    levels = [level] if level else range(100,900,100)
    for level in levels:
        resLvl = eval('session.Result{}.query.filter_by(mat_no=mat_no).first()'.format(level))
        resStr = eval('session.Result{}Schema().dump(resLvl)'.format(level))
        ans.append(resStr)
    return ans


def get_grading_rule(mat_no, ignore_404=False):
    db_name = get_DB(mat_no, ignore_404=ignore_404)
    if not db_name: return []
    db_name = db_name[:-3]
    session = load_session(db_name)
    grading_rule = session.GradingRule.query.all()[0].rule
    grading_rule = grading_rule.split(',')
    return grading_rule


def get_grading_point(mat_no):
    grading_rule = get_grading_rule(mat_no)
    return dict(map(lambda x: x.split()[:-1], grading_rule))


def get_registered_courses(mat_no, level=None, true_levels=False):
    # Get courses registered for all levels if level=None else for level
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    courses_registered = defaultdict(dict)
    if level and not true_levels:
        levels = [level]
        levs = level
    else:
        levels = range(100, 900, 100)
        levs = 100

    first_not_found = True
    for _level in levels:
        courses_regd = eval('session.CourseReg{}.query.filter_by(mat_no=mat_no).first()'.format(_level))
        courses_regd_str = eval('session.CourseReg{}Schema().dump(courses_regd)'.format(_level))
        courses_registered[levs] = {'courses': [], 'table': 'CourseReg{}'.format(_level)}
        for course in courses_regd_str:
            if courses_regd_str[course] == '1':
                courses_registered[levs]['courses'].append(course)
        courses_registered[levs]['courses'] = sorted(courses_registered[levs]['courses'])

        if true_levels:
            if courses_regd_str != {} and levs != 100 and len(courses_registered[levs]['courses']) == 0 and first_not_found:
                first_not_found = False
                del courses_registered[levs]
                levs -= 100
                courses_registered[levs] = {'courses': [], 'table': 'CourseReg{}'.format(_level)}

        if 'carryovers' in courses_regd_str and courses_regd_str['carryovers']:
            if courses_regd_str['carryovers'] != '0':
                courses_registered[levs]['courses'].extend(sorted(courses_regd_str['carryovers'].split(',')))

        courses_registered[levs]['course_reg_level'] = courses_regd_str['level'] if 'level' in courses_regd_str else None
        courses_registered[levs]['course_reg_session'] = courses_regd_str['session'] if 'session' in courses_regd_str else None
        courses_registered[levs]['probation'] = courses_regd_str['probation'] if 'probation' in courses_regd_str else None
        courses_registered[levs]['fees_status'] = courses_regd_str['fees_status'] if 'fees_status' in courses_regd_str else None
        courses_registered[levs]['others'] = courses_regd_str['others'] if 'others' in courses_regd_str else None
        levs += 100
    if level:
        return courses_registered[level]
    return courses_registered


def get_attribute_names(cls):
    return [prop.key for prop in class_mapper(cls).iterate_properties
        if isinstance(prop, sqlalchemy.orm.ColumnProperty)]


def compute_gpa(mat_no, ret_json=True):
    person = loads(personal_info.get(mat_no=mat_no))
    mode_of_entry = person['mode_of_entry']
    gpas = [[0, 0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0]][mode_of_entry - 1]
    level_percent = [[10, 15, 20, 25, 30], [10, 20, 30, 40], [25, 35, 40]][mode_of_entry - 1]
    level_credits = get_credits(mat_no, mode_of_entry)
    grade_weight = get_grading_point(mat_no)

    for result in loads(result_statement.get(mat_no))["results"]:
        for record in (result["first_sem"] + result["second_sem"]):
            (course, grade) = (record[1], record[5])
            course_props = loads(course_details.get(course))
            lvl = int(course_props["course_level"] / 100) - 1
            if mode_of_entry != 1:
                if course in ['GST111', 'GST112', 'GST121', 'GST122', 'GST123']:
                    lvl = 0
                else:
                    lvl -= 1
            credit = course_props["course_credit"]
            product = int(grade_weight[grade]) * credit
            gpas[lvl] += (product / level_credits[lvl])

    if ret_json:
        return dumps(gpas)
    else:
        return gpas


def get_gpa_credits(mat_no, session=None):
    if not session:
        db_name = get_DB(mat_no)[:-3]
        session = load_session(db_name)
    stud = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
    gpa_credits = stud.level100, stud.level200, stud.level300, stud.level400, stud.level500
    gpas, credits = [], []
    for gpa_credit in gpa_credits:
        if gpa_credit:
            gpa, credit = list(map(float, gpa_credit.split(',')))
            credit = int(credit)
        else: gpa, credit = None, None
        gpas.append(gpa)
        credits.append(credit)

    return gpas, credits


def get_level_weightings(mod):
    if mod == 1: return [.1, .15, .2, .25, .3]
    elif mod == 2: return [0, .1, .2, .3, .4]
    else: return [0, 0, .25, .35, .4]


def compute_grade(mat_no, score, ignore_404=False):
    if score > 100 or score < 0:
        return ''
    grading_rules = [rule.split(' ') for rule in get_grading_rule(mat_no, ignore_404=ignore_404)]
    if not grading_rules: return ''
    grading_rules = sorted(grading_rules, key=lambda x: int(x[2]), reverse=True)
    for index in range(len(grading_rules)):
        if score >= int(grading_rules[index][2]):
            return grading_rules[index][0]
    return ''


def compute_category(mat_no, result_level, session_taken, total_credits, credits_passed):
    entry_session = result_statement.get(mat_no, 0)['entry_session']
    previous_categories = [x['category'] for x in result_poll(mat_no, 0) if x and x['session'] < session_taken]

    if total_credits == credits_passed: return 'A'
    if result_level == 100 and entry_session >= 2014:
        if credits_passed >= 36: return 'B'
        elif 23 <= credits_passed < 36: return 'C'
        else:
            if 'C' in previous_categories: return 'E' # Handle condition for transfer
            else: return 'D'
    else:
        percent_passed = credits_passed / total_credits * 100
        if percent_passed >= 50: return 'B'
        elif 25 <= percent_passed < 50: return 'C'
        else:
            if 'C' not in previous_categories: return 'D'
            else: return 'E'


def get_category_for_unregistered_students(level):
    """
    Retrieves the category for unregistered students

    :param level: level of students
    :return: category of unregistered students
    """
    group = 'unregistered students'
    if level >= 500:
        cat_obj = Category500.query.filter_by(group=group).first()
    else:
        cat_obj = Category.query.filter_by(group=group).first()

    return cat_obj.category


def get_category_for_absent_students(level):
    """
    Retrieves the category for students with absent cases

    :param level: level of students
    :return: category of students with absent cases
    """
    if level >= 500:
        group = 'carryover students'
        cat_obj = Category500.query.filter_by(group=group).first()
    else:
        group = 'absent from examination'
        cat_obj = Category.query.filter_by(group=group).first()

    return cat_obj.category


def get_category(mat_no, level, session=None):
    """
    Retrieves the category of a students with mat_no `mat_no` from the database

    :param mat_no: mat_no of student
    :param level: level of student
    :param session: (Optional) session module object of student
    :return: category of student
    """
    if not session:
        db_name = get_DB(mat_no)[:-3]
        session = load_session(db_name)
    res_obj = eval('session.Result{}'.format(level))
    student = res_obj.query.filter_by(mat_no=mat_no).first()
    if student:
        category = student.category
    else:
        course_reg_obj = eval('session.CourseReg{}'.format(level))
        registered_courses = bool(course_reg_obj.query.filter_by(mat_no=mat_no).first())
        # Should probably apply this to the db
        if registered_courses:
            category = get_category_for_unregistered_students(level)
        else:
            category = get_category_for_absent_students(level)

    return category


def get_num_of_prize_winners():
    """
    Retrieves the number of prize winners

    :return: number of prize winners
    """
    # TODO: Query this from the master db
    return 1

