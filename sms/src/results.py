"""
This module facilitates entry of results to the students' databases as
well as updating gpa record of the student


******** IMPORTANT NOTICE ********

* Unusual results are results for courses written but not registered
     by the student for the session
* Roses are red!

"""
import os.path
from copy import deepcopy
from sms.src import course_reg_utils, personal_info, course_details, utils
from sms.src.users import access_decorator


@access_decorator
def get(mat_no, acad_session):
    return get_results_for_acad_session(mat_no, acad_session)


@access_decorator
def post(list_of_results):
    if not list_of_results:
        return 'No result record supplied', 400

    result_acad_sessions = list(set(list(zip(*list_of_results))[1]))
    current_session = utils.get_current_session()
    if len(result_acad_sessions) > 1:
        return 'You are only authorised to add results for the current session. ' \
               'Remove entries from other sessions and try again', 401

    elif int(result_acad_sessions[0]) != current_session:
        return 'You are not authorised to add results for the past session: ' \
               '{}/{}'.format(current_session, current_session + 1), 401

    return add_result_records(list_of_results)


@access_decorator
def put(list_of_results):
    if not list_of_results:
        return 'No result record supplied', 400
    return add_result_records(list_of_results)


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
        [results.pop(key) for key in ['mat_no', 'session']]
        category = results.pop('category')
        tcp = results.pop('tcp')
        level_written = results.pop('level')
        carryovers = utils.serialize_carryovers(results.pop('carryovers'))
        unusual_results = utils.serialize_carryovers(results.pop('unusual_results'))

        # flatten the result dictionary
        regular_courses = [[crse_code] + results[crse_code].split(',') for crse_code in results if results[crse_code]]
        regular_courses.extend(carryovers)

        # enrich the course lists
        fields = ('course_credit', 'course_semester', 'course_level')
        regular_courses = course_reg_utils.enrich_course_list(regular_courses, fields=fields)
        unusual_results = course_reg_utils.enrich_course_list(unusual_results, fields=fields)

        # get the actual carryovers
        carryovers = list(filter(lambda x: x[5] < level_written, regular_courses))
        regular_courses = list(filter(lambda x: x[5] == level_written, regular_courses))

        [unusual_results[index].append('Course not registered') for index in range(len(unusual_results))]
        [regular_courses[index].append('') for index in range(len(regular_courses))]

    elif return_empty:
        regular_courses, carryovers, unusual_results = [], [], []
        level_written, tcp, category = '', 0, ''
    else:
        return 'No result available for entered session', 404

    regular_courses = split_courses_by_semester(multisort(regular_courses), 4)
    carryovers = split_courses_by_semester(multisort(carryovers), 4)
    unusual_results = split_courses_by_semester(multisort(unusual_results), 4)

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


def add_result_records(list_of_results):
    """  ==== JSON FORMAT FOR THE RESULTS ====

    res =[
            ["MEE351", "2019", "ENG1503886", "98"],
            ["MEE491", "2019", "ENG1503886", "98"],
            ["EMA481", "2019", "ENG1503886", "98"],
            ["MEE531", "2019", "ENG1503886", "98"],
            ["MEE561", "2019", "ENG1503886", "98"],
            ["MEE571", "2019", "ENG1503886", "98"]
        ]
    """
    base_dir = os.path.dirname(__file__)
    result_errors_file = open(os.path.join(base_dir, '../../result_errors.txt'), 'a')
    error_log = []

    # todo: initialize a dictionary of course details here and pass to "add_single_result_record"
    #       this should include all the courses in set(list_of_results[*][0])
    #       or grow this dictionary lazily

    for index, result_details in enumerate(list_of_results):
        errors, status_code = add_single_result_record(index, result_details, result_errors_file)
        error_log.extend(errors)

    result_errors_file.close()
    print('\n====>>  ', '{} result entries added with {} errors'.format(len(list_of_results), len(error_log)))

    if len(list_of_results) == len(error_log):
        return error_log, 400

    return error_log, 200


def add_single_result_record(index, result_details, result_errors_file):
    """

    :param index: position of entry in the larger list --for tracking
    :param result_details: [course_code, session_written, mat_no, score]
    :param result_errors_file: file object in write or append mode for logging important errors
    :return:
    """
    course_code, session_taken, mat_no, score = result_details
    session_taken, score = map(int, [session_taken, score])
    grade = utils.compute_grade(score, utils.get_DB(mat_no))
    error_log = []

    # Error check on grade and score
    if not (0 <= score <= 100):
        error_text = "Unexpected value for score, '{}', for {} at index {}; " \
                     "result not added".format(score, mat_no, index)
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print('\n[WARNING]: ', error_log[-1])
        return error_log, 403

    if not grade:
        error_text = '{0} at index {1} was not found in the database'.format(mat_no, index)
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print('\n[WARNING]: ', error_log[-1])
        return error_log, 404

    try:
        course_dets = course_details.get(course_code, 0)
    except Exception as e:
        error_text = '{} at index {} was not found in the database'.format(course_code, index)
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print('\n[WARNING]: ', error_log[-1])
        return error_log, 404

    course_credit = course_dets['course_credit']
    course_level = course_dets['course_level']
    is_unusual = False
    full_course_reg = utils.get_registered_courses(mat_no)
    course_registration = course_reg_utils.get_course_reg_at_acad_session(session_taken, full_course_reg)

    if course_registration == {}:
        course_registration = {'course_reg_level': utils.get_level(mat_no), 'courses': []}
        is_unusual = True
        error_log.append('No course registration found for {0} at index {1} for the '
                         '{2}/{3} session'.format(mat_no, index, session_taken, session_taken + 1))
        print('\n====>>  ', error_log[-1])

    courses_registered = course_registration['courses']
    if not is_unusual and course_code not in courses_registered:
        is_unusual = True
        error_log.append('{0} at index {1} did not register {2} in the {3}/{4} '
                         'session'.format(mat_no, index, course_code, session_taken, session_taken + 1))
        print('\n====>>  ', error_log[-1])

    try:
        db_name = utils.get_DB(mat_no)
        session = utils.load_session(db_name)
    except ImportError:
        return 'Student not found in database', 403

    level_written = course_registration['course_reg_level']
    res_poll = utils.result_poll(mat_no)
    result_record, table_to_populate = utils.get_result_at_acad_session(session_taken, res_poll)

    try:
        result_xxx_schema = eval('session.{}Schema()'.format(table_to_populate))
    except AttributeError:
        # table_to_populate is empty, this would be redefined
        pass
    except ImportError:
        return '{} table does not exist'.format(table_to_populate), 403

    if not result_record:
        table_to_populate = get_table_to_populate(course_registration, res_poll)
        result_xxx_schema = eval('session.{}Schema()'.format(table_to_populate))
        params = mat_no, session_taken, courses_registered, result_xxx_schema, level_written
        result_record = prepare_new_results_table(*params)

    # Check if a previous entry for the course exists the session and log changes
    # also modifies the value of "previous_grade"
    previous_grade = get_previous_grade_and_log_changes(result_details, result_record, is_unusual)

    # add score to result object
    if is_unusual or result_record['unusual_results']:
        unusual_results = result_record['unusual_results'].split(',')
        index = [ind for ind, x in enumerate(unusual_results) if x.split(' ')[0] == course_code]
        if index: unusual_results.pop(index[0])
        if is_unusual: unusual_results.append('{} {} {}'.format(course_code, score, grade))
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
    if not courses_registered:
        # todo test this for when it should be 'D'
        previous_categories = [x['category'] for x in res_poll if x and x['category'] and x['session'] < session_taken]
        result_record['category'] = 'E' if 'C' in previous_categories else 'D'
    else:
        if grade not in ['F', 'ABS'] and previous_grade in ['F', 'ABS', ''] and not is_unusual:
            result_record['tcp'] += course_credit
        tcr, tcp = course_registration['tcr'], result_record['tcp']
        result_record['category'] = utils.compute_category(mat_no, level_written, session_taken, tcr, tcp)

    res_record = result_xxx_schema.load(result_record)
    db_session = result_xxx_schema.Meta.sqla_session
    db_session.add(res_record)
    db_session.commit()
    db_session.close()

    if not is_unusual:
        # update GPA - Credits table
        error, status = update_gpa_credits(mat_no, grade, previous_grade, course_credit, course_level)
        if status != 200:
            return error, status

    return error_log, 400


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
        level_credits = creds[index + (len(creds) - 5)]
        grading_point_rule = utils.get_grading_point(utils.get_DB(mat_no))
        grading_point = int(grading_point_rule[grade])
        grading_point_old = int(grading_point_rule[previous_grade]) if previous_grade else 0

        level_gpa = level_gpa + ((course_credit * (grading_point - grading_point_old)) / level_credits)
        level_credits_passed += course_credit

    gpa_credits[index] = (round(level_gpa, 4), level_credits_passed)
    cgpa = 0
    mode_of_entry = personal_info.get(mat_no)['mode_of_entry']
    weights = utils.get_level_weightings(mode_of_entry)
    while 0 in weights: weights.remove(0)
    for idx in range(1, len(weights)+1):
        cgpa += weights[-idx] * gpa_credits[-idx][0] if gpa_credits[-idx] and gpa_credits[-idx][0] else 0

    gpa_record = {'mat_no': mat_no, 'cgpa': cgpa}
    for key, idx in [('level{}00'.format(lev+1), lev) for lev in range(5)]:
        gpa_record.update({key: ','.join(list(map(str, gpa_credits[idx]))) if gpa_credits[idx][0] else None})

    gpa_record = session.GPACreditsSchema().load(gpa_record)
    db_session = session.GPACreditsSchema().Meta.sqla_session
    db_session.add(gpa_record)
    db_session.commit()
    db_session.close()
    return '', 200


# =========================================================================================
#                                   Utility functions
# =========================================================================================

def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    iters = sorted(iters, key=lambda x: x[0][3])
    # iters = sorted(iters, key=lambda x: x[4])  # no longer be needed as I'm splitting the semesters later on
    return iters


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
        print('\n====>>  ', 'moving result record {} for {} from store to result table'.format(course_code, mat_no))

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
            previous_grade = ''

        if previous_score not in ['-1', score]:
            print('\n====>>   overwriting previous {} result of {} for the {}/{} session: '
                  '{} ==> {}'.format(course_code, mat_no, session_taken, int(session_taken) + 1, previous_score, score))
        
        if previous_grade != 'ABS':
            return previous_grade
    return ''


def calculate_category_deprecated(result_record, courses_registered):
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
        credit = course_details.get(course, 0)['course_credit']
        crs_grade = [x[1] for x in result_courses if x[0] == course]
        if crs_grade and crs_grade[0] not in ['F', 'ABS']:
            credits_passed += credit
        total_credits += credit

    category = utils.compute_category(mat_no, level_written, session_taken, total_credits, credits_passed)
    return category


def split_courses_by_semester(course_list, semester_value_index):
    """

    :param course_list: [ ('course_code', 'some_other_detail', ...), (..), ... ]
    :param semester_index: the index of each course where the semester value can be found
    :return:
    """
    split_course_list = [list(filter(lambda x: x[semester_value_index] == sem, course_list)) for sem in (1, 2)]
    dic = {
        'first_sem': dictify(split_course_list[0], key_index=0),
        'second_sem': dictify(split_course_list[1], key_index=0),
    }
    return dic


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
        dic[lis.pop(key_index)] = lis
    return dic

# todo: write function to recalculate category, gpa-credits and cgpa
