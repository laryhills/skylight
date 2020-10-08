"""
This module facilitates entry of results to the students' databases as
well as updating gpa record of the student


******** IMPORTANT NOTICE ********

* Unusual results are results for courses written but not registered by the student for the session
* To delete a result entry, post the result as normal but with score = -1

"""
import os.path
from colorama import init, Fore, Style

from sms.config import db
from sms.models.master import Props
from sms.src.course_reg_utils import course_reg_for_session
from sms.src.script import get_students_for_course_adviser
from sms.src.users import access_decorator
from sms.src import result_statement, personal_info, course_details, utils

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
def get_single_results_stats(mat_no, level, acad_session):
    return _get_single_results_stats(mat_no, level, acad_session)


@access_decorator
def get_multiple_results_stats(acad_session, level):
    return _get_multiple_results_stats(acad_session, level)


@access_decorator
def get(mat_no, acad_session, include_reg=False):
    return get_results_for_acad_session(mat_no, acad_session, include_reg)


@access_decorator
def post(data, superuser=False):
    level = data.get('level', None)
    list_of_results = data.get('list_of_results', [])

    # check inputs
    if level is None:
        return 'Result entry level was not supplied', 400
    try:
        result_acad_sessions = list(map(int, list(set(list(zip(*list_of_results))[1]))))
    except ValueError:
        return 'At least one invalid entry for session present', 400
    except IndexError:
        return 'No result record supplied', 400

    if not superuser:
        current_session = utils.get_current_session()
        if len(result_acad_sessions) > 1:
            return 'You are only authorised to add results for the current session {}/{}. \nRemove entries from other' \
                   ' sessions and try again'.format(int(result_acad_sessions[0]), int(result_acad_sessions[0]) + 1), 401
        elif int(result_acad_sessions[0]) != current_session:
            return 'You are not authorised to add results for the past session: ' \
                   '{}/{}'.format(int(result_acad_sessions[0]), int(result_acad_sessions[0]) + 1), 401
    else: level = None

    return add_result_records(list_of_results, level)


# ==============================================================================================
#                                  Core functions
# ==============================================================================================

def get_results_for_acad_session(mat_no, acad_session, include_reg=False):
    """includes registered but unentered results if "include_reg" is True.

    Score and grade in such case are empty strings
    """
    res_stmt = result_statement.get(mat_no)
    res_idx = [(idx, res) for idx, res in enumerate(res_stmt['results']) if res['session'] == acad_session]
    if not res_idx and not include_reg:
        return 'No result available for entered session', 404

    res_idx, results = res_idx[0] if res_idx else ('', {'first_sem': [], 'second_sem': []})
    if include_reg:
        from sms.src.course_reg import get_existing_course_reg
        reg, ret_code = get_existing_course_reg(mat_no, acad_session)
        if ret_code != 200:
            return reg, ret_code

        # include courses from course_reg not present
        for sem in ('first_sem', 'second_sem'):
            entered_res = list(zip(*results[sem]))[1] if results[sem] else []
            to_be_entered = list(filter(lambda x: x[0] not in entered_res, reg['courses'][sem]))
            results[sem].extend([['', *crs[:3], '', '', *crs[3:]] for crs in to_be_entered])

        if res_idx == '':
            results['level'] = reg['course_reg_level']
            results['session'] = reg['course_reg_session']
            results['table'] = int(reg['table_to_populate'][-3:])

    regular_courses, carryovers, unusual_results = refine_results(results)
    gpa_credits = utils.gpa_credits_poll(mat_no)
    personal_info_keys = ('surname', 'othernames', 'sex', 'grad_status', 'is_symlink', 'mode_of_entry')
    frame = {'mat_no': mat_no,
             'name': res_stmt["surname"] + " " + res_stmt["othernames"],
             'personal_info': {key: res_stmt[key] for key in personal_info_keys},
             'entry_session': res_stmt["session_admitted"],
             'table': 'Result{}'.format(100 * (res_idx + 1)) if res_idx != '' else res_idx,
             'level_written': results['level'],
             'session_written': results['session'],
             'tcp': res_stmt['credits'][res_idx][1] if res_idx else 0,
             'category': res_stmt['category'][res_idx] if res_idx else '',
             'level_gpa': gpa_credits[utils.ltoi(min(results['level'], 500))][0],
             'cgpa': gpa_credits[-1],
             'regular_courses': regular_courses,
             'carryovers': carryovers,
             'unusual_results': utils.dictify(utils.multisort(res_stmt['unusual_results'][res_idx]))
             }
    return frame, 200


def _get_multiple_results_stats(acad_session, level):
    students = get_students_for_course_adviser(level, acad_session=acad_session)
    result_details = []
    result_details_incomplete = []

    for mat_no in students:
        details, _ = _get_single_results_stats(mat_no, level, acad_session)
        if details[2] == details[3] and details[2] != 0:
            result_details.append(details)
        else:
            result_details_incomplete.append(details)
    result_details = sorted(result_details, key=lambda x: x[0])
    result_details.extend(sorted(result_details_incomplete, key=lambda x: x[0]))
    return result_details, 200


def _get_single_results_stats(mat_no, level, acad_session):
    info = personal_info.get(mat_no)
    name = info['surname'] + ' ' + info['othernames']
    reg_courses = course_reg_for_session(mat_no, acad_session)
    reg_course_codes = reg_courses.get('courses', [])
    tcr = reg_courses.get('tcr', 0)
    res, _ = res_poll_for_session(acad_session, mat_no=mat_no)
    tce, carryovers_dict, remark = 0, {}, ''

    if res:
        carryovers = res.pop('carryovers')
        carryovers_list = [] if not carryovers else carryovers.split(',')
        for course_dets in carryovers_list:
            code, _, _ = course_dets.split(' ')
            carryovers_dict[code] = True

    for course_code in reg_course_codes:
        if res.get(course_code) not in [None, '-1,ABS'] or carryovers_dict.get(course_code) not in [None, '-1,ABS']:
            tce += course_details.get(course_code)['credit']

    return [mat_no, name, tcr, tce, remark], 200


def add_result_records(list_of_results, level=None):
    """
    :param list_of_results: [
             [course_code_1, session_written_1, mat_no_1, score_1], ...]
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
        idx = index + 1  # start index at 1
        errors = add_single_result_record(idx, result_details, result_errors_file, course_details_dict, level)
        error_log.extend(errors)

    result_errors_file.close()
    print(Fore.CYAN, '====>>  ', '{} result entries added with {} errors'.format(
        len(list_of_results), len(error_log)), Style.RESET_ALL)

    return error_log or ['Done'], 200


def add_single_result_record(index, result_details, result_errors_file, course_details_dict, level=None):
    """
    :param index: position of entry in the larger list --for tracking
    :param result_details: [course_code, session_written, mat_no, score]
    :param result_errors_file: file object in write or append mode for logging important errors
    :param course_details_dict:
    :param level: student's course-adviser assigned level
    """
    error_log = []
    try:
        course_code, session_taken, mat_no, score = result_details
        session_taken, score = map(int, [session_taken, score])
        entry_session = utils.get_DB(mat_no)
    except:
        return handle_errors('Invalid inputs at index {}'.format(index), error_log, result_errors_file, result_details)

    grade = utils.compute_grade(score, entry_session)
    current_level = utils.get_level(mat_no)

    # Error check on level, grade and score
    error_text = ''
    if level:
        levels = [600, 700, 800] if level == 600 else [level]
        if current_level not in levels:
            error_text = "You are not allowed to enter results for {} at index {} whose current level is " \
                         "{}".format(mat_no, index, current_level)
    if not (-1 <= score <= 100) and not error_text:
        error_text = 'Unexpected score for {}, "{}", for {} at index {}; ' \
                     'result not added'.format(course_code, score, mat_no, index)
    if not grade and not error_text:
        error_text = '{0} at index {1} was not found in the database'.format(mat_no, index)
    if error_text:
        return handle_errors(error_text, error_log, result_errors_file, result_details)

    # Get course details
    if course_code in course_details_dict and course_details_dict[course_code]:
        course_dets = course_details_dict[course_code]
    else:
        # if there was error in initializing course_details_dict, individual calls would be made
        course_dets = course_details.get(course_code)
        if not course_dets:
            # fail on non-existent course(s)
            error_text = '{} at index {} was not found in the database'.format(course_code, index)
            return handle_errors(error_text, error_log, result_errors_file, result_details)

    course_credit = course_dets['credit']
    course_level = course_dets['level']
    is_unusual = False

    # Get course reg
    course_registration = course_reg_for_session(mat_no, session_taken) or {'level': current_level, 'courses': []}
    courses_registered = course_registration['courses']
    level_written = course_registration['level']
    if not courses_registered:
        is_unusual = True
        error_log = handle_errors('No course registration found for {0} at index {1} for the {2}/{3} '
                                  'session'.format(mat_no, index, session_taken, session_taken + 1), error_log)
    elif course_code not in courses_registered:
        is_unusual = True
        error_log = handle_errors('{0} at index {1} did not register {2} in the {3}/{4} session'
                                  ''.format(mat_no, index, course_code, session_taken, session_taken + 1), error_log)

    # Get the result table for the session
    res_poll = utils.result_poll(mat_no)
    result_record, table_to_populate = res_poll_for_session(session_taken, res_poll)
    session = utils.load_session(utils.get_DB(mat_no))
    if not result_record:
        if is_unusual and grade == 'ABS':
            return handle_errors('Unregistered course {} with grade "ABS" cannot be added for '
                                 '{}'.format(course_code, mat_no), error_log)
        table_to_populate = get_table_to_populate(course_registration, res_poll)
        result_xxx_schema = getattr(session, table_to_populate + 'Schema')()
        params = mat_no, session_taken, courses_registered, result_xxx_schema, level_written
        result_record = prepare_new_results_table(params)
    else:
        result_xxx_schema = getattr(session, table_to_populate + 'Schema')()

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
    # todo: do sth with "owed_courses_exist"
    if not courses_registered:
        tcr, tcp = 0, 0
    else:
        if grade not in ['F', 'ABS'] and previous_grade in ['F', 'ABS', ''] and not is_unusual:
            result_record['tcp'] += course_credit
        elif grade in ['F', 'ABS'] and previous_grade not in ['F', 'ABS', ''] and not is_unusual:
            result_record['tcp'] -= course_credit
        tcr, tcp = course_registration['tcr'], result_record['tcp']

    res_record = result_xxx_schema.load(result_record)
    res_record.category = utils.compute_category(tcr, res_record)

    db_session = result_xxx_schema.Meta.sqla_session
    db_session.add(res_record)
    if grade == 'ABS':
        delete_if_empty(res_record, result_xxx_schema)
    db_session.commit()
    db_session.close()

    # update GPA - Credits table
    if not is_unusual:
        update_gpa_credits(mat_no, grade, previous_grade, course_credit, course_level)

    return error_log


def update_gpa_credits(mat_no, grade, previous_grade, course_credit, course_level):
    gpa_credits = utils.gpa_credits_poll(mat_no)[:-1]
    index = utils.ltoi(course_level)
    level_gpa = gpa_credits[index][0] if gpa_credits[index][0] else 0
    level_credits_passed = gpa_credits[index][1] if gpa_credits[index][1] else 0

    if grade != previous_grade:
        creds = utils.get_credits(mat_no, lpad=True)
        level_credits = creds[index]
        grading_point_rule = utils.get_grading_point(utils.get_DB(mat_no))
        grading_point = int(grading_point_rule[grade])
        grading_point_old = int(grading_point_rule[previous_grade]) if previous_grade else 0

        diff = grading_point - grading_point_old
        level_gpa = level_gpa + ((course_credit * diff) / level_credits)

        sign_multiplier = diff // abs(diff) if diff != 0 else 0
        level_credits_passed += course_credit * sign_multiplier

    gpa_credits[index] = (round(level_gpa, 4), level_credits_passed)
    cgpa = 0
    mode_of_entry = personal_info.get(mat_no)['mode_of_entry']
    weights = utils.get_level_weightings(mode_of_entry)

    for idx in range(len(weights)):
        cgpa += weights[idx] * gpa_credits[idx][0] if gpa_credits[idx] and gpa_credits[idx][0] else 0

    gpa_record = {'mat_no': mat_no, 'cgpa': round(cgpa, 4)}
    for key, idx in [('level{}00'.format(lev+1), lev) for lev in range(5)]:
        gpa_record.update({key: ','.join(list(map(str, gpa_credits[idx]))) if gpa_credits[idx][0] else None})

    session = utils.load_session(utils.get_DB(mat_no))
    gpa_record = session.GPACreditsSchema().load(gpa_record)
    db_session = session.GPACreditsSchema().Meta.sqla_session
    db_session.add(gpa_record)
    db_session.commit()
    db_session.close()
    return 'Success'


def delete_if_empty(res_record, result_xxx_schema):
    regulars = result_xxx_schema.dump(res_record)
    [regulars.pop(key) for key in ['mat_no', 'session', 'category', 'tcp', 'level']]
    carrys = [utils.spc_fn(x) for x in utils.csv_fn(regulars.pop('carryovers'))]
    unusuals = [utils.spc_fn(x) for x in utils.csv_fn(regulars.pop('unusual_results'))]

    regulars_exist = any([res for res in regulars if regulars[res] and regulars[res] != '-1,ABS'])
    exists = lambda crs_list: any([res[0] for res in crs_list if res[2] != 'ABS'])
    carryovers_exist, unusual_results_exist = [exists(crs_list) for crs_list in (carrys, unusuals)]
    if not any([regulars_exist, carryovers_exist, unusual_results_exist]):
        # delete the db entry
        result_xxx_schema.Meta.sqla_session.delete(res_record)


# =========================================================================================
#                                   Utility functions
# =========================================================================================

def get_table_to_populate(session_course_reg, res_poll):
    """selecting Result table for a fresh input (first result entered for the student for the session)

       - use table corresponding to course reg table if available
       - else use table corresponding to result level if available
       - otherwise find the first free table from Result100 to Result800
    """
    level_written = session_course_reg['level']
    if session_course_reg['courses'] and not res_poll[utils.ltoi(int(session_course_reg['table'][-3:]))]:
        table_to_populate = 'Result' + session_course_reg['table'][-3:]
    elif not res_poll[utils.ltoi(level_written)]:
        table_to_populate = 'Result' + str(level_written)
    else:
        index = [ind for ind, x in enumerate(res_poll) if not x]
        table_to_populate = 'Result' + str(100 * (index[0] + 1))
    return table_to_populate


def prepare_new_results_table(params):
    mat_no, session_taken, courses_registered, result_xxx_schema, level_written = params
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
        # we search for carryovers with param level=900 to bypass get_carryovers ignoring
        #  unregistered 500 level courses when the when the student's level is 500
        owed_courses = utils.get_carryovers(mat_no, level=900)
        owed_courses = utils.dictify(owed_courses['first_sem']), utils.dictify(owed_courses['second_sem'])
        course_code, course_semester = course_dets['code'], course_dets['semester']
        if course_code in owed_courses[course_semester - 1]:
            owed_courses[course_semester - 1].pop(course_code)
        if not owed_courses[0] and not owed_courses[1] and grade not in ['F', 'ABS']:
            return False
    return True


def refine_results(res_from_stmt):
    """post processing of result object from result_statement"""
    lvl_norm = min(500, res_from_stmt['level'])  # normalise the level
    regulars, carryovers, unusuals = [{'first_sem': {}, 'second_sem': {}} for _ in range(3)]
    for sem in ('first_sem', 'second_sem'):
        for res in utils.multisort(res_from_stmt[sem], key_idx=1):
            [carryovers, regulars][res[6] == lvl_norm][sem].update(utils.dictify(list([res[1:7]])))
    # TODO process unusual results when it gets added to result statement
    return regulars, carryovers, unusuals


def handle_errors(error_text, error_log_array=None, error_file=None, result_details=None):
    if error_file and result_details: error_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
    if error_log_array is not None: error_log_array.append(error_text)
    if error_text != '': print(Fore.RED, '[WARNING]: ', error_text, Style.RESET_ALL)
    return error_log_array or []


def res_poll_for_session(acad_session, res_poll=None, mat_no=None):
    """supply mat_no if res_poll is not given"""
    if not res_poll: res_poll = utils.result_poll(mat_no)
    ind_res = [[ind, res] for ind, res in enumerate(res_poll) if res and res['session'] == acad_session]
    ind_res = ({}, '') if not ind_res else (ind_res[0][1], 'Result{}'.format(100 * (ind_res[0][0] + 1)))
    return ind_res
