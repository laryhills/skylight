from re import match
from json import loads
from sms import config
from operator import add
from functools import reduce
from concurrent.futures.process import ProcessPoolExecutor
from sms.models.master import Category, Category500, Props
from sms.src import personal_info, course_details, result_statement, users

'''
Handle frequently called or single use simple utility functions
These aren't exposed endpoints and needn't return json data
'''

# FUNCTION MAPPINGS
get_DB = users.get_DB
get_level = users.get_level
load_session = users.load_session
get_current_session = config.get_current_session

# LAMBDAS
ltoi = lambda x: x//100 - 1
dictify = lambda flat_list: {x[0]:x[1:] for x in flat_list}
multisort = lambda iters: sorted(iters, key=lambda x:x[0][3]+x[0])
query = lambda cls, col, key: cls.query.filter(col == key).first()
csv_fn = lambda csv, fn=lambda x:x: list(map(fn, csv.split(","))) if csv else []
spc_fn = lambda spc, fn=lambda x:x: list(map(fn, spc.split(" "))) if spc else []


# DB POLLS
def get_dept(full=True):
    dept = csv_fn(Props.query.filter_by(key="Department").first().valuestr)
    return dept[full]


def get_max_reg_credits(conditional=False):
    key = ["MaxRegCredits", "CondMaxRegCredits500"][conditional]
    return Props.query.filter_by(key=key).first().valueint


def get_session_from_level(session, level, reverse=False):
    session_list = csv_fn(Props.query.filter_by(key="SessionList").first().valuestr, int)
    idx = session_list.index(session) + [ltoi(level), 1 - level//100][reverse]
    return session_list[idx]


def get_num_of_prize_winners():
    "Retrieves the number of prize winners"
    return Props.query.filter_by(key="NumPrizeWinners").first().valueint


def get_grading_point(session):
    # TODO use spc_fn and/or csv_fn, dict values should be int not str
    grading_rules = load_session(session).GradingRule.query.first().rule.split(",")
    return dict(map(lambda x: x.split()[:-1], grading_rules))


def get_level_weightings(mode_of_entry, lpad=True):
    "Get fraction each level GPA contributes to final CGPA for specified entry mode"
    percentages = Props.query.filter_by(key="LevelPercent").first().valuestr
    level_percent = [spc_fn(x,lambda x: int(x)/100) for x in csv_fn(percentages)][mode_of_entry - 1]
    if lpad:
        return [0] * (mode_of_entry - 1) + level_percent
    return level_percent


def gpa_credits_poll(mat_no):
    "Poll level GPAs, credits and CGPA for student from DB"
    session = load_session(get_DB(mat_no))
    student = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
    ret_val = [student.cgpa]
    for lvl in range(500,0,-100):
        ret_val.append(csv_fn(getattr(student, f"level{lvl}") or "null,null", loads))
    return ret_val[::-1]


def course_reg_poll(mat_no, table=None):
    """Get the course reg of a student as seen on CourseReg Table.
    Specify table for particular table, else returns from all CourseReg tables"""
    session, crs_regs = load_session(get_DB(mat_no)), []
    for table in [table] if table else range(100,900,100):
        reg_tbl = getattr(session, f"CourseReg{table}").query.filter_by(mat_no=mat_no).first()
        crs_reg = getattr(session, f"CourseReg{table}Schema")().dump(reg_tbl)
        crs_reg["courses"] = []
        for key, val in crs_reg.copy().items():
            if match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", key):
                if crs_reg.pop(key):
                    crs_reg["courses"].append(key)
        # TODO CorseReg100 has carryover default as 0, fix in DB
        crs_reg["courses"] += csv_fn(crs_reg.pop("carryovers", ""))
        crs_regs.append(crs_reg)
    return crs_regs


def result_poll(mat_no, table=None):
    """Get the results of a student as seen in Results Table.
    Specify table for particular table, else returns from all Result tables"""
    db_name = get_DB(mat_no)
    if not db_name:
        return None
    session, results = load_session(db_name), []
    for table in [table] if table else range(100,900,100):
        res_tbl = getattr(session, f"Result{table}").query.filter_by(mat_no=mat_no).first()
        result = getattr(session, f"Result{table}Schema")().dump(res_tbl)
        results.append(result)
    return results


def get_credits(mat_no=None, mode_of_entry=None, session=None, lpad=False):
    "Returns a list of total credits for each level"
    if mat_no:
        session = get_DB(mat_no)
        mode_of_entry = mode_of_entry or personal_info.get(mat_no)["mode_of_entry"]
    session = load_session(session)
    Credits, CreditsSchema = session.Credits, session.CreditsSchema

    credits = CreditsSchema().dump(Credits.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_credits = [credits["level{}".format(lvl)] for lvl in range(mode_of_entry*100,600,100)]
    if lpad:
        return [0] * (mode_of_entry - 1) + level_credits
    return level_credits


def get_courses(mat_no=None, mode_of_entry=None, session=None, lpad=True):
    "Returns student/session courses list for all levels"
    if mat_no:
        session = get_DB(mat_no)
        mode_of_entry = mode_of_entry or personal_info.get(mat_no)["mode_of_entry"]
    session = load_session(session)
    Courses, CoursesSchema = session.Courses, session.CoursesSchema

    courses = CoursesSchema().dump(Courses.query.filter_by(mode_of_entry=mode_of_entry).first())
    level_courses = [courses["level{}".format(lvl)].split(" ") for lvl in range(mode_of_entry*100,600,100)]
    level_courses = [[csv_fn(x[0]), csv_fn(x[1])] for x in level_courses]
    if lpad:
        return [ [[], []] for x in range(mode_of_entry - 1) ] + level_courses
    return level_courses


# UTILITIES
def get_carryovers(mat_no, level=None, next_level=False):
    """
    Returns a dictionary of the carryover courses for a student for each semester
    :param level: Courses up to but not including this level which are not passed
    :param next_level: Courses up to and including level which are not passed
    """
    level = level or get_level(mat_no)
    first_sem, second_sem = set(), set()
    for course in get_courses(mat_no)[:ltoi(level)+next_level]:
        first_sem |= set(course[0])
        second_sem |= set(course[1])

    person_options = csv_fn(personal_info.get(mat_no)["option"])
    if person_options:
        for choice in person_options:
            for option in course_details.get_options():
                if choice in option["members"]:
                    idx = option["semester"] - 1
                    [first_sem, second_sem][idx] -= set(option["members"])
                    [first_sem, second_sem][idx] |= {choice}

    results = result_statement.get(mat_no)["results"]
    res_first_sem, res_second_sem = [], []
    if results:
        res_first_sem = reduce(add, [result["first_sem"] for result in results])
        res_second_sem = reduce(add, [result["second_sem"] for result in results])
    first_sem -= set([record[1] for record in res_first_sem if record[5] not in ("F", "ABS")])
    second_sem -= set([record[1] for record in res_second_sem if record[5] not in ("F", "ABS")])

    category = ([None] + result_statement.get(mat_no)["category"])[-1]
    if category == "C" and level in (200, 300, 400):
        # Handle probation carryovers
        first_sem |= set(get_courses(mat_no)[ltoi(level)][0])
        second_sem |= set(get_courses(mat_no)[ltoi(level)][1])

    carryovers = {"first_sem":[],"second_sem":[]}
    courses = [("first_sem", course) for course in first_sem] + [("second_sem", course) for course in second_sem]
    for sem, failed_course in courses:
        course = course_details.get(failed_course)
        carryovers[sem].append([failed_course, course["credit"], course["level"]])
    return carryovers


def compute_grade(score, session):
    grading_rules = load_session(session).GradingRule.query.first().rule.split(",")
    for grade, weight, cutoff in [x.split() for x in grading_rules]:
        if 100 >= score >= int(cutoff):
            return grade
    return ''


def get_degree_class(mat_no=None, cgpa=None, acad_session=None):
    "Get the degree-class text for student"
    # TODO only lower limit is used, why both boundaries stored?
    acad_session = acad_session or get_DB(mat_no)
    cgpa = cgpa or gpa_credits_poll(mat_no)[-1]
    session = load_session(acad_session)
    deg_classes = [(csv_fn(x.limits,loads)[0], x.cls) for x in session.DegreeClass.query.all()]
    for cutoff, deg_class in deg_classes:
        if cgpa >= cutoff:
            return deg_class


def compute_category(tcr, Result):
    entry_session = int(get_DB(Result.mat_no)[:4])
    results = result_statement.get(Result.mat_no)
    tcp, session, level = Result.tcp, Result.session, Result.level
    level_credits = get_credits(Result.mat_no, lpad=True)[ltoi(level)]
    tables = [ltoi(x["table"]) for x in results["results"] if x["session"] < session]
    prev_probated = "C" in [results["category"][i] for i in tables]
    # Add previous passed credits for 100L probated students
    if level == 100 and prev_probated:
        tcp += sum([results["credits"][i][1] for i in tables])
    if tcp == tcr:
        return "A"
    if tcr == 0:
        return ["H", "K"][level < 500]
    # TODO pull categories from DB, Handle owed_courses_exist, Handle condition for transfer
    categories = {x: {100:[(78.26,"B"), (50,"C"), (0,"D")]} for x in range(2014,get_current_session()+1)}
    catg_rule = {**categories.get(entry_session), 500:[(0, "B")]}.get(level,[(50,"B"), (25,"C"), (0,"D")])
    percent_passed = tcp / level_credits * 100
    for lower, catg in catg_rule:
        if percent_passed >= lower:
            category = catg
            break
    # Handle if probated before
    if category == "C" and prev_probated:
        category = "E"
    return category


def get_category(mat_no, level, acad_session, session=None):
    if not session:
        db_name = get_DB(mat_no)
        session = load_session(db_name)
    start_level = level
    while start_level <= 800:
        res_obj = eval('session.Result{}'.format(start_level))
        student = res_obj.query.filter_by(mat_no=mat_no).first()
        if not student:
            break
        if student.session == acad_session:
            return student.category
        start_level += 100
    else:
        # guys who could never have sat for the exam in `acad_session` session
        return ['H', 'K'][level < 500]
    course_reg_obj = eval('session.CourseReg{}'.format(start_level))
    registered_courses = bool(course_reg_obj.query.filter_by(mat_no=mat_no).first())
    if registered_courses:
        return ['B', 'G'][level < 500]
    else:
        return ['H', 'K'][level < 500]


# NOT YET REFACTORED
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


# DEPRECATED
def get_result_at_acad_session(acad_session, res_poll=None, mat_no=None):
    # TODO deprecate and use result_poll in a list comprehension
    # preferably result statement instead if can be helped
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
