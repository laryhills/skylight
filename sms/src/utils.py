from sms import config
from json import loads, dumps
from sms.models.courses import Options, OptionsSchema
from concurrent.futures.process import ProcessPoolExecutor
from sms.models.master import Category, Category500, Props
from sms.src import personal_info, course_details, result_statement, users

'''
Handle frequently called or single use simple utility functions
These aren't exposed endpoints and needn't return json data
'''

get_DB = users.get_DB
get_level = users.get_level
load_session = users.load_session
get_current_session = config.get_current_session
csv_fn = lambda csv: csv.split(",") if csv else []


def get_dept(full=True):
    dept = loads(Props.query.filter_by(key="Department").first().valuestr)
    return dept[full]


def get_session_from_level(entry_session, level):
    session_list = loads(Props.query.filter_by(key="SessionList").first().valuestr)
    idx = session_list.index(entry_session) + level//100 - 1
    return session_list[idx]


def get_entry_session_from_level(session, level):
    session_list = loads(Props.query.filter_by(key="SessionList").first().valuestr)
    idx = session_list.index(session) - level//100 + 1
    return session_list[idx]


def get_maximum_credits_for_course_reg():
    normal = Props.query.filter_by(key="MaxRegCredits").first().valueint
    clause_of_51 = Props.query.filter_by(key="CondMaxRegCredits500").first().valueint
    return {"normal": normal, "clause_of_51": clause_of_51}


def get_credits(mat_no=None, mode_of_entry=1, session=None, lpad=False):
    "Returns a list of total credits for each level"
    if mat_no:
        session = get_DB(mat_no)
        mode_of_entry = personal_info.get(mat_no)["mode_of_entry"]
    session = load_session(session)
    Credits, CreditsSchema = session.Credits, session.CreditsSchema

    credits = CreditsSchema().dump(Credits.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_credits = [credits["level{}".format(lvl)] for lvl in range(mode_of_entry*100,600,100)]
    if lpad:
        return [0] * (mode_of_entry - 1) + level_credits
    return level_credits


def get_courses(mat_no=None, mode_of_entry=1, session=None, lpad=True):
    "Returns student/session courses list for all levels"
    if mat_no:
        session = get_DB(mat_no)
        mode_of_entry = personal_info.get(mat_no)["mode_of_entry"]
    session = load_session(session)
    Courses, CoursesSchema = session.Courses, session.CoursesSchema

    courses = CoursesSchema().dump(Courses.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_courses = [courses["level{}".format(lvl)].split(" ") for lvl in range(mode_of_entry*100,600,100)]
    level_courses = [[csv_fn(x[0]), csv_fn(x[1])] for x in level_courses]
    if lpad:
        return [ [[], []] for x in range(mode_of_entry - 1) ] + level_courses
    return level_courses


def get_carryovers(mat_no, level=None, next_level=False):
    """
    Returns a dictionary of the carryover courses for a student
    :param level: (Optional) level of the student
    :param current: (Optional) if True returns carryovers up to the current academic session of the student
    """
    level = level or get_level(mat_no)
    first_sem, second_sem = set(), set()
    results = result_statement.get(mat_no)["results"]
    for course in get_courses(mat_no)[:level//100+next_level-1]:
        first_sem |= set(course[0])
        second_sem |= set(course[1])

    person_options = csv_fn(personal_info.get(mat_no)["option"])
    if person_options:
        options = [OptionsSchema().dump(option) for option in Options.query.all()]
        for choice in person_options:
            for option in options:
                if choice in option["members"]:
                    idx = option["semester"] - 1
                    [first_sem, second_sem][idx] -= set(option["members"].split(","))
                    [first_sem, second_sem][idx] |= {choice}

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
        # TODO chk if lpad necessary in get_courses
        first_sem |= set(get_courses(mat_no)[int(level/100)-1][0])
        second_sem |= set(get_courses(mat_no)[int(level/100)-1][1])

    carryovers = {"first_sem":[],"second_sem":[]}
    for failed_course in first_sem:
        course_dets = course_details.get(failed_course)
        credit = course_dets["course_credit"]
        course_lvl = course_dets["course_level"]
        carryovers["first_sem"].append([failed_course, str(credit), course_lvl])
    for failed_course in second_sem:
        course_dets = course_details.get(failed_course)
        credit = course_dets["course_credit"]
        course_lvl = course_dets["course_level"]
        carryovers["second_sem"].append([failed_course, str(credit), course_lvl])
    return carryovers


def result_poll(mat_no, level=None):
    """
    Get the results of a student

    Returns the result for all levels if `level` is None else for `level`

    :param mat_no: mat number of student
    :param level: level of the result
    :return: List of results
    """
    db_name = get_DB(mat_no)
    session = load_session(db_name)
    ans=[]
    levels = [level] if level else range(100,900,100)
    for level in levels:
        resLvl = eval('session.Result{}.query.filter_by(mat_no=mat_no).first()'.format(level))
        resStr = eval('session.Result{}Schema().dump(resLvl)'.format(level))
        ans.append(resStr)
    return ans


def get_result_at_acad_session(acad_session, res_poll=None, mat_no=None):
    """
    Get results for a specific session
    
    :param acad_session: the session for which to fetch results
    :param res_poll: result of result_poll() 
    :param mat_no:  (optional) supply this only if res_poll is not given
    :return: a tuple: (result dictionary, table fetched from)
    """
    if not res_poll:
        res_poll = result_poll(mat_no)
    for index, result in enumerate(res_poll):
        if result and result['session'] == acad_session:
            table = 'Result' + str((index + 1) * 100)
            return result, table
    return {}, ''


def serialize_carryovers(carryover_string):
    """
    Serialize string containing carryover results into a list of results
    [[course_code, score, grade], [...], ...]
    
    :param carryover_string: 
    :return: 
    """
    if not carryover_string:
        return []
    carryovers = carryover_string.split(',')
    carryovers = [x.split(' ') for x in carryovers if carryovers]
    return carryovers


def compute_grade(score, session):
    if score == -1:
        return "ABS"
    if not 0 <= score <= 100:
        return None
    grading_rules = load_session(session).GradingRule.query.first().rule.split(",")
    for grade, weight, cutoff in [x.split() for x in grading_rules]:
        if score >= int(cutoff):
            return grade


def get_grading_point(session):
    grading_rules = load_session(session).GradingRule.query.first().rule.split(",")
    return dict(map(lambda x: x.split()[:-1], grading_rules))


def get_registered_courses(mat_no, db_level=None):
    """
    Get courses registered from all course reg tables if db_level=None else from "CourseReg<db_level>" table
    :param mat_no:
    :param db_level:
    :return:
    """
    db_name = get_DB(mat_no)
    session = load_session(db_name)
    levels = [db_level] if db_level else range(100, 900, 100)
    courses_registered = {}

    for _level in levels:
        courses_regd = eval('session.CourseReg{}'.format(_level)).query.filter_by(mat_no=mat_no).first()
        courses_regd_str = eval('session.CourseReg{}Schema()'.format(_level)).dump(courses_regd)
        courses_registered[_level] = {'courses': [], 'table': 'CourseReg{}'.format(_level)}
        if not courses_regd_str:
            continue

        courses_regd_str.pop('mat_no')
        carryovers = courses_regd_str.pop('carryovers')
        courses_registered[_level]['course_reg_session'] = courses_regd_str.pop('session')
        courses_registered[_level]['course_reg_level'] = courses_regd_str.pop('level')
        for field in ['probation', 'fees_status', 'others', 'tcr']:
            courses_registered[_level][field] = courses_regd_str.pop(field)

        for course in courses_regd_str:
            if courses_regd_str[course] in [1, '1']:
                courses_registered[_level]['courses'].append(course)

        courses_registered[_level]['courses'] = sorted(courses_registered[_level]['courses'])
        if carryovers and carryovers not in [0, '0', '']:
            courses_registered[_level]['courses'].extend(sorted(carryovers.split(',')))

    return courses_registered


def compute_gpa(mat_no, ret_json=True):
    person = personal_info.get(mat_no=mat_no)
    mode_of_entry = person['mode_of_entry']
    gpas = [[0, 0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0]][mode_of_entry - 1]
    level_percent = [[10, 15, 20, 25, 30], [10, 20, 30, 40], [25, 35, 40]][mode_of_entry - 1]
    # TODO check if lpad necessary, use props for level percent
    level_credits = get_credits(mat_no, mode_of_entry)
    grade_weight = get_grading_point(get_DB(mat_no))

    for result in result_statement.get(mat_no)["results"]:
        for record in (result["first_sem"] + result["second_sem"]):
            (course, grade) = (record[1], record[5])
            course_props = course_details.get(course)
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
        db_name = get_DB(mat_no)
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


def get_cgpa(mat_no):
    """
    fetch the current cgpa for student with mat_no from the student's entry session database

    NOTE: THIS DOES NOT DO ANY CALCULATIONS

    :param mat_no:
    :return:
    """
    db_name = get_DB(mat_no)
    session = load_session(db_name)
    student = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
    return student.cgpa


def get_session_degree_class(acad_session):
    """
    Get the degree-class dictionary for an academic session with lower limits as keys

    :param acad_session:
    :return:
    """
    session = load_session(acad_session)
    degree_class = session.DegreeClass.query.all()
    degree_class = {float(deg.limits.split(',')[0]): deg.cls for deg in degree_class}
    return degree_class


def compute_degree_class(mat_no, cgpa=None, acad_session=None):
    """
    get the degree-class text for graduated students

    :param mat_no:
    :param cgpa:
    :param acad_session:
    :return:
    """
    # todo extend this for non-graduated students
    if not cgpa: cgpa = get_cgpa(mat_no)
    if not acad_session: acad_session = int(get_DB(mat_no)[:4])

    degree_class = get_session_degree_class(acad_session)
    for lower_limit in sorted(degree_class.keys(), reverse=True):
        if cgpa >= lower_limit:
            return degree_class[lower_limit]
    return ''


def get_level_weightings(mod):
    if mod == 1: return [.1, .15, .2, .25, .3]
    elif mod == 2: return [0, .1, .2, .3, .4]
    else: return [0, 0, .25, .35, .4]


def compute_category(mat_no, level_written, session_taken, tcr, tcp, owed_courses_exist=True):
    """

    :param mat_no:
    :param level_written:
    :param session_taken:
    :param tcr: total credits registered for session
    :param tcp: total credits passed
    :param owed_courses_exist:
    :return:
    """
    # todo: Handle condition for transfer
    person = personal_info.get(mat_no)
    res_poll = result_poll(mat_no, 0)
    creds = get_credits(mat_no)

    entry_session = person['session_admitted']
    previous_categories = [x['category'] for x in res_poll if x and x['session'] < session_taken]

    # ensure to get the right value of level_credits irrespective of the size of the list (PUTME vs DE students)
    # TODO check lpad with get_credits
    index = (level_written // 100 - 1)
    level_credits = creds[index + (len(creds) - 5)]

    # add previous tcp to current for 100 level probation students
    if level_written == 100 and 'C' in previous_categories:
        tcp += sum([x['tcp'] for x in res_poll if x and x['level'] == level_written and x['session'] < session_taken])

    if level_written >= 500:
        if tcp == tcr and not owed_courses_exist: return 'A'
        else: return 'B'
    else:
        if tcr == 0:
            retval = 'D' if 'C' not in previous_categories else 'E'
            return retval
        elif tcp == tcr:
            return 'A'
        elif level_written == 100 and entry_session >= 2014:
            if tcp >= 36: return 'B'
            elif 23 <= tcp < 36: return 'C'
            elif 'C' not in previous_categories: return 'D'
            else: return 'E'
        else:
            percent_passed = tcp / level_credits * 100
            if percent_passed >= 50: return 'B'
            elif 25 <= percent_passed < 50: return 'C'
            elif 'C' not in previous_categories: return 'D'
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
        db_name = get_DB(mat_no)
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


def dictify(flat_list, key_index=0):
    """
    convert a flat list of lists (or tuples) to a dictionary, with the value at key_index as key
    :param flat_list:
    :param key_index:
    :return:
    """
    dic = {}
    for lis in flat_list:
        lis = list(lis)
        key = lis.pop(key_index)
        dic[key] = lis[0] if len(lis) == 1 and isinstance(lis[0], dict) else lis
    return dic


def multiprocessing_wrapper(func, iterable, context, use_workers=True, max_workers=None):
    """
    use multiprocessing to call a function on members of an iterable

    (number of workers limited to 5)

    :param func: the function to call
    :param iterable: items you want to call func on
    :param context: params that are passed to all instances
    :param use_workers: whether to spawn off child processes
    :param max_workers: maximum number of child processes to use
    :return:
    """
    if not use_workers:
        [func(item, *context) for item in iterable]
    else:
        max_workers = max_workers if max_workers else min(len(iterable), 4)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            [executor.submit(func, item, *context) for item in iterable]


def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    iters = sorted(iters, key=lambda x: x[0][3])
    return iters
