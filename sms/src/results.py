"""
This module facilitates entry of results to the students' databases as
well as updating gpa record of the student


******** IMPORTANT NOTICE ********

* Unusual results are results for courses written but not registered by the student for the session
* To delete a result entry, post the result as normal but with score = -1

"""
import os.path
from copy import deepcopy
from colorama import init, Fore, Style
from sms.src import course_reg_utils, personal_info, course_details, utils
from sms.src.users import access_decorator
from sms.src.script import get_students_by_level
from sms.models.master import Props
from sms.config import db

init()  # initialize colorama


def get_resultedit():
    state = Props.query.filter_by(key="ResultEdit").first().valueint
    return state, 200


@access_decorator
def set_resultedit(state):
    query = Props.query.filter_by(key="ResultEdit").first()
    query.valueint = int(bool(state))
    db.session.commit()
    return query.valueint, 200


@access_decorator
def get_result_details(mat_no, acad_session):
    return get_results(mat_no, acad_session)


@access_decorator
def get_single_results_stats(mat_no, level, acad_session):
    return _get_single_results_stats(mat_no, level, acad_session)


@access_decorator
def get_multiple_results_stats(acad_session, level):
    return _get_multiple_results_stats(acad_session, level)


@access_decorator
def get(mat_no, acad_session):
    return get_results_for_acad_session(mat_no, acad_session)


@access_decorator
def post(data, superuser=False):
    level = data.get('level', None)
    list_of_results = data.get('list_of_results', [])

    if not list_of_results: return 'No result record supplied', 400
    if not level: return 'Result entry level was not supplied', 400

    if not superuser:
        result_acad_sessions = list(set(list(zip(*list_of_results))[1]))
        current_session = utils.get_current_session()
        if len(result_acad_sessions) > 1:
            return 'You are only authorised to add results for the current session. ' \
                   'Remove entries from other sessions and try again', 401
        elif int(result_acad_sessions[0]) != current_session:
            return 'You are not authorised to add results for the past session: ' \
                   '{}/{}'.format(int(result_acad_sessions[0]), int(result_acad_sessions[0]) + 1), 401
    else: level = None

    return add_result_records(list_of_results, level)


# ==============================================================================================
#                                  Core functions
# ==============================================================================================

def get_results_for_acad_session(mat_no, acad_session, return_empty=False):
    """

    :param mat_no:
    :param acad_session:
    :param return_empty: return object with empty fields instead of 404
    :return:
    """
    res_poll = utils.result_poll(mat_no)
    results, table_to_populate = utils.get_result_at_acad_session(acad_session, res_poll)

    if results:
        # remove extra fields from results
        result, level_written, tcp, category = refine_res_poll_item(results)
    elif return_empty:
        result = {'regular_courses': [], 'carryovers': [], 'unusual_results': []}
        level_written, tcp, category = '', 0, ''
    else:
        return 'No result available for entered session', 404

    regular_courses = split_courses_by_semester(utils.multisort(result['regular_courses']), 4)
    carryovers = split_courses_by_semester(utils.multisort(result['carryovers']), 4)
    unusual_results = split_courses_by_semester(utils.multisort(result['unusual_results']), 4)

    frame = {'mat_no': mat_no,
             'table': table_to_populate,
             'level_written': level_written,
             'session_written': acad_session,
             'tcp': tcp,
             'regular_courses': regular_courses,
             'carryovers': carryovers,
             'unusual_results': unusual_results,
             'category': category,
             }
    return frame, 200


def get_results_for_level(mat_no, level_written, return_empty=False):
    """

    :param mat_no:
    :param level_written:
    :param return_empty: return object with empty fields instead of 404
    :return:
    """
    res_poll = utils.result_poll(mat_no)
    results = {res['session']: (index, res) for index, res in enumerate(res_poll) if res and res['level'] == level_written}
    result_for_level = {}

    for session in sorted(results.keys()):
        index, result = results[session]
        table = 'Result' + str((index + 1) * 100)
        if result:
            result, level_written, tcp, category = refine_res_poll_item(result)
        elif return_empty:
            result = {'regular_courses': [], 'carryovers': [], 'unusual_results': []}
            level_written, tcp, category = '', 0, ''
        else:
            continue

        regular_courses = split_courses_by_semester(utils.multisort(result['regular_courses']), 4)
        carryovers = split_courses_by_semester(utils.multisort(result['carryovers']), 4)
        unusual_results = split_courses_by_semester(utils.multisort(result['unusual_results']), 4)

        frame = {'mat_no': mat_no,
                 'table': table,
                 'level_written': level_written,
                 'session_written': session,
                 'tcp': tcp,
                 'regular_courses': regular_courses,
                 'carryovers': carryovers,
                 'unusual_results': unusual_results,
                 'category': category,
                 }
        result_for_level[session] = frame

    return result_for_level, 200


def get_results(mat_no, acad_session):
    from sms.src.course_reg import get_existing_course_reg

    reg, return_code = get_existing_course_reg(mat_no, acad_session)
    if return_code != 200:
        return reg, return_code

    res, _ = utils.get_result_at_acad_session(acad_session, mat_no=mat_no)
    if not res:
        session = reg.pop('course_reg_session')
        level = reg.pop('course_reg_level')
        carryovers = []
        unusual_results = ''
    else:
        session = res.pop('session')
        level = res.pop('level')
        carryovers = res.pop('carryovers')
        unusual_results = res.pop('unusual_results')

    details = reg['personal_info']
    regular_reg_courses = reg['courses']['first_sem'] + reg['courses']['second_sem']
    carryover_reg_courses = reg['choices']['first_sem'] + reg['choices']['second_sem']

    carryovers_dict = {}
    carryovers_list = [] if not carryovers else carryovers.split(',')
    for course in carryovers_list:
        course_code, score, grade = course.split(' ')
        carryovers_dict[course_code] = [int(score), grade]

    for course_dets in regular_reg_courses:
        course_code = course_dets[0]
        course_level = course_dets[-1]
        if course_level != level:
            carryover_reg_courses.append(course_dets)
            continue
        score, grade = res.get(course_code, ',').split(',')
        score, grade = ('', '') if score == '-1' else (score, grade)
        score = score if not score.isdecimal() else int(score)
        course_dets.pop()
        course_dets.extend([score, grade])

    for course_dets in carryover_reg_courses:
        if course_dets in regular_reg_courses:
            regular_reg_courses.remove(course_dets)
        course_code = course_dets[0]
        score, grade = carryovers_dict.get(course_code, ['', ''])
        score, grade = ('', '') if score == '-1' else (score, grade)
        course_dets.pop()
        course_dets.extend([score, grade])

    result_details = {
        'mat_no': mat_no,
        'name': details['surname'] + ' ' + details['othernames'],
        'level': level,
        'session': session,
        'result': regular_reg_courses,
        'carryovers': carryover_reg_courses,
        'unusual_results': unusual_results
    }

    return result_details, 200


def _get_multiple_results_stats(acad_session, level):
    entry_session = acad_session - (level / 100) + 1
    students = get_students_by_level(entry_session, level)
    result_details = []

    for mat_no in students:
        details, _ = _get_single_results_stats(mat_no, level, acad_session)
        result_details.append(details)

    return result_details, 200


def _get_single_results_stats(mat_no, level, acad_session):
    info = personal_info.get(mat_no)
    name = info['surname'] + ' ' + info['othernames']
    reg_courses = utils.get_registered_courses(mat_no, level)[level]
    reg_course_codes = reg_courses.get('courses', [])
    tcr = reg_courses.get('tcr', 0)
    res, _ = utils.get_result_at_acad_session(acad_session, mat_no=mat_no)
    tce, carryovers_dict, remark = 0, {}, ''

    if res:
        carryovers = res.pop('carryovers')
        carryovers_list = [] if not carryovers else carryovers.split(',')
        for course_dets in carryovers_list:
            code, _, _ = course_dets.split(' ')
            carryovers_dict[code] = True

    for course_code in reg_course_codes:
        if res.get(course_code) not in [None, '-1,ABS'] or carryovers_dict.get(course_code) not in [None, '-1,ABS']:
            tce += course_details.get(course_code)['course_credit']

    return [mat_no, name, tcr, tce, remark], 200


def add_result_records(list_of_results, level=None):
    """
    list_of_results =[
             [course_code_1, session_written_1, mat_no_1, score_1],

             [course_code_2, session_written_2, mat_no_2, score_2],

             ...
        ]
    :param list_of_results:
    :param level: level for the results being entered; to control course advisers' access
    :return:
    """
    base_dir = os.path.dirname(__file__)
    result_errors_file = open(os.path.join(base_dir, '../../result_errors.txt'), 'a')
    error_log = []

    # Initialize a dictionary of course details for all courses in list_of_results
    courses = list(set(list(zip(*list_of_results))[0]))
    try:
        course_details_dict = {course: course_details.get(course) for course in courses}
    except:
        # for any error, set this to an empty dict, individual calls will be made
        # and the error course would fail gracefully
        course_details_dict = {}

    for index, result_details in enumerate(list_of_results):
        errors, status_code = add_single_result_record(index, result_details, result_errors_file, course_details_dict, level)
        error_log.extend(errors)

    result_errors_file.close()
    print(Fore.CYAN, '====>>  ', '{} result entries added with {} errors'.format(
        len(list_of_results), len(error_log)), Style.RESET_ALL)

    return error_log, 200


def add_single_result_record(index, result_details, result_errors_file, course_details_dict, level=None):
    """

    :param index: position of entry in the larger list --for tracking
    :param result_details: [course_code, session_written, mat_no, score]
    :param result_errors_file: file object in write or append mode for logging important errors
    :param course_details_dict:
    :param level: the level for which results is being entered
    :return:
    """
    course_code, session_taken, mat_no, score = result_details
    session_taken, score = map(int, [session_taken, score])
    grade = utils.compute_grade(score, utils.get_DB(mat_no))
    current_level = utils.get_level(mat_no)
    error_log = []

    # Error check on level, grade and score
    if level:
        levels = [600, 700, 800] if level == 600 else [level]
        if current_level not in levels:
            error_text = "You are not allowed to enter results for {} at index {} whose current level is {}. " \
                         "Please meet the {} level course adviser".format(mat_no, index, current_level, current_level)
            result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
            error_log.append(error_text)
            print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL)
            return error_log, 403

    if not (-1 <= score <= 100):
        error_text = "Unexpected value for score, '{}', for {} at index {}; " \
                     "result not added".format(score, mat_no, index)
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL)
        return error_log, 403

    if not grade:
        error_text = '{0} at index {1} was not found in the database'.format(mat_no, index)
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL)
        return error_log, 404

    if course_code in course_details_dict and course_details_dict[course_code]:
        course_dets = course_details_dict[course_code]
    else:
        # if there was error in initializing course_details_dict, individual calls would be made
        course_dets = course_details.get(course_code)
        if not course_dets:
            # fail on non-existent course(s)
            error_text = '{} at index {} was not found in the database'.format(course_code, index)
            result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
            error_log.append(error_text)
            print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL,)
            return error_log, 404

    course_credit = course_dets['course_credit']
    course_level = course_dets['course_level']
    is_unusual = False
    full_course_reg = utils.get_registered_courses(mat_no)
    course_registration = course_reg_utils.get_course_reg_at_acad_session(session_taken, full_course_reg)

    if course_registration == {}:
        course_registration = {'course_reg_level': current_level, 'courses': []}
        is_unusual = True
        error_log.append('No course registration found for {0} at index {1} for the '
                         '{2}/{3} session'.format(mat_no, index, session_taken, session_taken + 1))
        print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL)

    courses_registered = course_registration['courses']
    if not is_unusual and course_code not in courses_registered:
        is_unusual = True
        error_log.append('{0} at index {1} did not register {2} in the {3}/{4} '
                         'session'.format(mat_no, index, course_code, session_taken, session_taken + 1))
        print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL)

    try:
        db_name = utils.get_DB(mat_no)
        session = utils.load_session(db_name)
    except ImportError:
        return 'Student not found in database', 403

    level_written = course_registration['course_reg_level']
    res_poll = utils.result_poll(mat_no)
    result_record, table_to_populate = utils.get_result_at_acad_session(session_taken, res_poll)

    try:
        result_xxx_schema = getattr(session, table_to_populate + 'Schema')()
    except AttributeError:
        # table_to_populate is empty, this would be redefined
        pass
    except ImportError:
        return '{} table does not exist'.format(table_to_populate), 403

    if not result_record:
        if is_unusual and grade == 'ABS':
            error_log.append('Unregistered course {} with grade "ABS" cannot be added for {}'.format(course_code, mat_no))
            print(Fore.RED, '[WARNING]: ', error_log[-1], Style.RESET_ALL)
            return error_log, 200

        table_to_populate = get_table_to_populate(course_registration, res_poll)
        result_xxx_schema = eval('session.{}Schema()'.format(table_to_populate))
        params = mat_no, session_taken, courses_registered, result_xxx_schema, level_written
        result_record = prepare_new_results_table(*params)

    # Check if a previous entry for the course exists in the current session and updates the value
    # of "previous_grade" while logging the changes to be made
    previous_grade = get_previous_grade_and_log_changes(result_details, result_record, is_unusual)

    # add score to result object
    if is_unusual or result_record['unusual_results']:
        unusual_results = result_record['unusual_results'].split(',')
        index = [ind for ind, x in enumerate(unusual_results) if x.split(' ')[0] == course_code]
        if index: unusual_results.pop(index[0])
        if is_unusual and grade != "ABS": unusual_results.append('{} {} {}'.format(course_code, score, grade))
        while '' in unusual_results: unusual_results.remove('')
        result_record['unusual_results'] = ','.join(unusual_results)
    if not is_unusual:
        if course_code in result_record:
            result_record[course_code] = '{},{}'.format(score, grade)
        else:
            carryovers = result_record['carryovers'].split(',') if result_record['carryovers'] else ['']
            index = [ind for ind, x in enumerate(carryovers) if x.split(' ')[0] == course_code]
            if index: carryovers.pop(index[0])
            carryovers.append('{} {} {}'.format(course_code, score, grade))
            while '' in carryovers: carryovers.remove('')
            result_record['carryovers'] = ','.join(carryovers)

    # get the session category
    owed_courses_exist = check_owed_courses_exists(mat_no, level_written, grade, course_dets) if not is_unusual else True
    if not courses_registered:
        tcr, tcp = 0, 0
    else:
        if grade not in ['F', 'ABS'] and previous_grade in ['F', 'ABS', ''] and not is_unusual:
            result_record['tcp'] += course_credit
        elif grade in ['F', 'ABS'] and previous_grade not in ['F', 'ABS', ''] and not is_unusual:
            result_record['tcp'] -= course_credit
        tcr, tcp = course_registration['tcr'], result_record['tcp']
    result_record['category'] = utils.compute_category(mat_no, level_written, session_taken, tcr, tcp, owed_courses_exist)

    res_record = result_xxx_schema.load(result_record)
    db_session = result_xxx_schema.Meta.sqla_session
    db_session.add(res_record)
    if grade == 'ABS':
        delete_if_empty(res_record, result_record, db_session)
    db_session.commit()
    db_session.close()

    status = 400
    if not is_unusual:
        # update GPA - Credits table
        error, status = update_gpa_credits(mat_no, grade, previous_grade, course_credit, course_level)
        if status != 200:
            error_log.append(error)

    return error_log, status


def update_gpa_credits(mat_no, grade, previous_grade, course_credit, course_level):
    try:
        db_name = utils.get_DB(mat_no)
        session = utils.load_session(db_name)
    except ImportError:
        return 'Student not found in database', 403

    gpa_credits = list(zip(*utils.get_gpa_credits(mat_no)))
    index = (course_level // 100 - 1)
    level_gpa = gpa_credits[index][0] if gpa_credits[index][0] else 0
    level_credits_passed = gpa_credits[index][1] if gpa_credits[index][1] else 0

    if grade != previous_grade:
        creds = utils.get_credits(mat_no)
        # ensure to get the right value irrespective of the size of the list (PUTME vs DE students)
        # TODO use lpad param with get_credits to keep uniform
        level_credits = creds[index + (len(creds) - 5)]
        grading_point_rule = utils.get_grading_point(utils.get_DB(mat_no))
        grading_point = int(grading_point_rule[grade]) if grade != 'ABS' else 0
        grading_point_old = int(grading_point_rule[previous_grade]) if previous_grade else 0

        level_gpa = level_gpa + ((course_credit * (grading_point - grading_point_old)) / level_credits)

        sign_multiplier = (grading_point - grading_point_old) // abs(grading_point - grading_point_old)
        level_credits_passed += course_credit * sign_multiplier

    gpa_credits[index] = (round(level_gpa, 4), level_credits_passed)
    cgpa = 0
    mode_of_entry = personal_info.get(mat_no)['mode_of_entry']
    weights = utils.get_level_weightings(mode_of_entry)
    while 0 in weights: weights.remove(0)

    for idx in range(1, len(weights)+1):
        cgpa += weights[-idx] * gpa_credits[-idx][0] if gpa_credits[-idx] and gpa_credits[-idx][0] else 0

    gpa_record = {'mat_no': mat_no, 'cgpa': round(cgpa, 4)}
    for key, idx in [('level{}00'.format(lev+1), lev) for lev in range(5)]:
        gpa_record.update({key: ','.join(list(map(str, gpa_credits[idx]))) if gpa_credits[idx][0] else None})

    gpa_record = session.GPACreditsSchema().load(gpa_record)
    db_session = session.GPACreditsSchema().Meta.sqla_session
    db_session.add(gpa_record)
    db_session.commit()
    db_session.close()
    return '', 200


def delete_if_empty(res_record, result_record, db_session):
    retval = strip_res_poll_item(result_record)
    regulars_exist = any([res for res in retval[0] if retval[0][res] and retval[0][res] != '-1,ABS'])
    # check carryovers, unusual results and regular courses in this order for any course
    if not (retval[4] or retval[5] or regulars_exist):
        db_session.delete(res_record)


# =========================================================================================
#                                   Utility functions
# =========================================================================================

def get_table_to_populate(session_course_reg, full_res_poll):
    level_written = session_course_reg['course_reg_level']
    # selecting Result table for a fresh input (first result entered for the student for the session)

    if session_course_reg['courses'] and not full_res_poll[int(session_course_reg['table'][-3:]) // 100 - 1]:
        # use table corresponding to course reg table if available
        table_to_populate = 'Result' + session_course_reg['table'][-3:]

    elif not full_res_poll[level_written // 100 - 1]:
        # use table corresponding to result level if available
        table_to_populate = 'Result' + str(level_written)

    else:
        # find the first free table from Result100 to Result800
        table_to_populate = 'Result' + str(100 * ([ind for ind, result in enumerate(full_res_poll) if not result][0] + 1))

    return table_to_populate


def prepare_new_results_table(mat_no, session_taken, courses_registered, result_xxx_schema, level_written):
    # preparing the new table

    table_columns = result_xxx_schema.load_fields.keys()
    result_record = {'mat_no': mat_no, 'session': session_taken, 'level': level_written, 'category': None,
                     'carryovers': '', 'unusual_results': '', 'tcp': 0}

    # prefill -1,ABS for courses in course_reg for new table
    for course in courses_registered:
        if course in table_columns:
            result_record[course] = '-1,ABS'
        else:
            carryovers = result_record['carryovers'].split(',')
            carryovers.append(str(course) + ' -1 ABS')
            while '' in carryovers: carryovers.remove('')
            result_record['carryovers'] = ','.join(carryovers)
    [result_record.update({col: None}) for col in set(table_columns).difference(set(result_record.keys()))]
    return result_record


def get_previous_grade_and_log_changes(result_details, result_record, is_unusual):
    course_code, session_taken, mat_no, score = result_details

    if not is_unusual and result_record['unusual_results'] and course_code in result_record['unusual_results']:
        print(Fore.CYAN, '[INFO]  ', 'moving result record {} for {} from store to result table'.format(
            course_code, mat_no), Style.RESET_ALL)

    elif (course_code in result_record and result_record[course_code]) or (
            course_code in result_record['carryovers']) or (course_code in result_record['unusual_results']):
        previous_score, previous_grade = '', ''

        if course_code in result_record and result_record[course_code]:
            previous_score, previous_grade = result_record[course_code].split(',')

        elif course_code in result_record['carryovers']:
            carryovers = result_record['carryovers'].split(',')
            previous_score, previous_grade = [x.split(' ')[1:] for x in carryovers if x.split(' ')[0] == course_code][0]

        elif course_code in result_record['unusual_results']:
            unusual_results = result_record['unusual_results'].split(',')
            previous_score = [x.split(' ')[1] for x in unusual_results if x.split(' ')[0] == course_code][0]
            previous_grade = ''  # the grade for unusual result should not be supplied as they contribute nothing

        if previous_score not in ['-1', score]:
            print(Fore.CYAN, '[INFO]   overwriting previous {} result of {} for the {}/{} session: '
                  '{} ==> {}'.format(course_code, mat_no, session_taken, int(session_taken) + 1, previous_score, score))
        
        if previous_grade != 'ABS':
            return previous_grade
    return ''


def check_owed_courses_exists(mat_no, level_written, grade, course_dets):
    if level_written >= 500:
        # we search for carryovers with param level=900 to bypass get_carryovers ignoring unregistered
        # 500 level courses when the when the student's level is 500
        owed_courses = utils.get_carryovers(mat_no, level=900, retJSON=False)
        owed_courses = utils.dictify(owed_courses['first_sem']), utils.dictify(owed_courses['second_sem'])
        course_code, course_semester = course_dets['course_code'], course_dets['course_semester']
        if course_code in owed_courses[course_semester - 1]:
            owed_courses[course_semester - 1].pop(course_code)

        if not owed_courses[0] and not owed_courses[1] and grade not in ['F', 'ABS']:
            return False
    return True


def calculate_category_deprecated(result_record, courses_registered):
    """

    :param result_record: a session's result record from result poll
    :param courses_registered: a list of course_codes for courses registered
    :return:
    """
    results_object = deepcopy(result_record)
    mat_no = results_object.pop('mat_no')
    session_taken = results_object.pop('session')
    level_written = results_object.pop('level')
    carryovers = results_object.pop('carryovers')
    results_object.pop('tcp')
    results_object.pop('category')
    results_object.pop('unusual_results')

    carryovers = carryovers.split(',') if carryovers else []
    carryovers = [[x.split(' ')[0], x.split(' ')[2]] for x in carryovers if carryovers]
    result_courses = [[x, results_object[x].split(',')[1]] for x in results_object if results_object[x]]
    result_courses.extend(carryovers)
    total_credits, credits_passed = 0, 0
    for course in courses_registered:
        credit = course_details.get(course)['course_credit']
        crs_grade = [x[1] for x in result_courses if x[0] == course]
        if crs_grade and crs_grade[0] not in ['F', 'ABS']:
            credits_passed += credit
        total_credits += credit

    category = utils.compute_category(mat_no, level_written, session_taken, total_credits, credits_passed)
    return category


def split_courses_by_semester(course_list, semester_value_index):
    """

    :param course_list: [ ('course_code', 'some_other_detail', ...), (..), ... ]
    :param semester_value_index: the index of each course where the semester value can be found
    :return:
    """
    split_course_list = [list(filter(lambda x: x[semester_value_index] == sem, course_list)) for sem in (1, 2)]
    dic = {
        'first_sem': utils.dictify(split_course_list[0], key_index=0),
        'second_sem': utils.dictify(split_course_list[1], key_index=0),
    }
    return dic


def refine_res_poll_item(res_poll_item):
    stripped_res_poll, category, tcp, level_written, carryovers, unusual_results = strip_res_poll_item(res_poll_item)

    # flatten the result dictionary
    regular_courses = [[crse_code] + stripped_res_poll[crse_code].split(',') for crse_code in stripped_res_poll if stripped_res_poll[crse_code]]
    regular_courses.extend(carryovers)

    # enrich the course lists
    fields = ('course_credit', 'course_semester', 'course_level')
    regular_courses = course_reg_utils.enrich_course_list(regular_courses, fields=fields)
    unusual_results = course_reg_utils.enrich_course_list(unusual_results, fields=fields)

    # get the actual carryovers
    # use a normalized level_written to account for spillover students (treated as 500 level students)
    level_written_alpha = 500 if level_written > 500 else level_written
    carryovers = list(filter(lambda x: x[5] < level_written_alpha, regular_courses))
    regular_courses = list(filter(lambda x: x[5] == level_written_alpha, regular_courses))

    [unusual_results[index].append('Course not registered') for index in range(len(unusual_results))]
    [regular_courses[index].append('') for index in range(len(regular_courses))]

    results = {
        'regular_courses': regular_courses,
        'carryovers': carryovers,
        'unusual_results': unusual_results
    }
    return results, level_written, tcp, category


def strip_res_poll_item(res_poll_item):
    res_poll_item = res_poll_item.copy()
    [res_poll_item.pop(key) for key in ['mat_no', 'session']]
    category = res_poll_item.pop('category')
    tcp = res_poll_item.pop('tcp')
    level_written = res_poll_item.pop('level')
    carryovers = utils.serialize_carryovers(res_poll_item.pop('carryovers'))
    unusual_results = utils.serialize_carryovers(res_poll_item.pop('unusual_results'))
    return res_poll_item, category, tcp, level_written, carryovers, unusual_results
