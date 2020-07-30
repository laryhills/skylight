import os.path
from copy import deepcopy
from sms import utils, course_reg_utils
from sms import course_details
from sms.users import access_decorator
# from sms.config import db, app
# from sqlalchemy.orm import sessionmaker, scoped_session


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


def get_results_for_acad_session(mat_no, acad_session):
    """

    :param mat_no:
    :param acad_session:
    :return:
    """
    res_poll = utils.result_poll(mat_no)
    results, table_to_populate = utils.get_result_at_acad_session(acad_session, res_poll)
    if results == {}:
        return 'No result available for entered session', 404

    # remove extra fields from results
    [results.pop(key) for key in ['mat_no', 'category', 'session', 'tcp']]
    result_level = results.pop('level')
    carryovers = utils.serialize_carryovers(results.pop('carryovers'))
    unusual_results = utils.serialize_carryovers(results.pop('unusual_results'))

    # flatten the result dictionary
    all_courses = [[crse_code] + results[crse_code].split(',') for crse_code in results if results[crse_code]]
    all_courses.extend(carryovers)

    # check if anything in course_reg is not in results...
    # todo refactor this to use -1,ABS
    course_reg = utils.get_registered_courses(mat_no)
    registered_courses = course_reg_utils.get_course_reg_at_acad_session(acad_session, course_reg)['courses']
    reg_extras = [[x, '', ''] for x in set(registered_courses).difference(set(list(zip(*all_courses))[0]))]

    # enrich the course lists
    all_courses = course_reg_utils.enrich_course_list(all_courses, fields=('course_credit', 'course_semester'))
    reg_extras = course_reg_utils.enrich_course_list(reg_extras, fields=('course_credit', 'course_semester'))
    unusual_results = course_reg_utils.enrich_course_list(unusual_results, fields=('course_credit', 'course_semester'))

    [reg_extras[index].append('Registered, no result') for index in range(len(reg_extras))]
    [reg_extras[index].append('Course not registered') for index in range(len(reg_extras))]
    [all_courses[index].append('') for index in range(len(all_courses))]

    all_courses.extend(reg_extras + unusual_results)
    frame = {'mat_no': mat_no,
             'table': table_to_populate,
             'level_written': result_level,
             'session_written': acad_session,
             'courses': multisort(all_courses)}
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
    result_errors_file = open(os.path.join(base_dir, 'result_errors.txt'), 'a')
    error_log = []

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

    :param index: position of entry in a larger list --for tracking
    :param result_details: [course_code, session_written, mat_no, score]
    :param result_errors_file: file object in write or append mode for logging important errors
    :return:
    """
    # todo: rewrite based on changes to db
    course_code, session_taken, mat_no, score = result_details
    session_taken, score = map(int, [session_taken, score])
    grade = utils.compute_grade(mat_no, score)
    error_log = []

    # Error check on grade and score
    if not grade:
        error_text = '{0} at index {1} was not found in the database'.format(mat_no, index)
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print('\n[WARNING]: ', error_log[-1])
        return error_log, 404

    if not (-1 <= score <= 100):
        error_text = "Unexpected value for score, '{}', for {} at index {}; " \
                     "result not added".format(score, mat_no, index)
        # todo: extend this to include user, datetime, etc.
        result_errors_file.writelines(str(result_details) + '  error: ' + error_text + '\n')
        error_log.append(error_text)
        print('\n[WARNING]: ', error_log[-1])
        return error_log, 403

    is_unusual = False
    previous_entry_grade = ''  # for updating GPA value

    course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
    course_registration = {}
    for key in course_reg:
        if course_reg[key]['course_reg_session'] == session_taken:
            course_registration = course_reg[key]
            break

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

    result_level = course_registration['course_reg_level']
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
        # preparing the new table
        table_to_populate = get_table_to_populate(course_registration, res_poll)
        result_xxx_schema = eval('session.{}Schema()'.format(table_to_populate))
        table_columns = result_xxx_schema.load_fields.keys()
        result_record = {'mat_no': mat_no, 'session': session_taken, 'level': result_level, 'category': None,
                         'carryovers': '', 'unusual_results': '', 'tcp': 0}
        for col in set(table_columns).intersection(set(result_record.keys())):
            if col not in result_record:
                result_record[col] = None
                # todo prefill -1,ABS for courses in course_reg for new table

    # Check if a previous entry for the course exists for session
    if not is_unusual and result_record['unusual_results'] and course_code in result_record['unusual_results']:
        # todo check for prefilled -1,ABS... I guess "is_first" flag would be useful here
        print('\n====>>  ', 'moving result record {} for {} from store to result table'.format(course_code, mat_no))
    elif (course_code in result_record and result_record[course_code]) or (
            course_code in result_record['carryovers']) or (course_code in result_record['unusual_results']):
        old = ''
        if course_code in result_record and result_record[course_code]:
            old, previous_entry_grade = result_record[course_code].split(',')
        elif course_code in result_record['carryovers']:
            carryovers = result_record['carryovers'].split(',')
            old, previous_entry_grade = [x.split(' ')[1:] for x in carryovers if x.split(' ')[0] == course_code][0]
        elif course_code in result_record['unusual_results']:
            unusual_results = result_record['unusual_results'].split(',')
            old = [x.split(' ')[1] for x in unusual_results if x.split(' ')[0] == course_code][0]
        print('\n====>>  ', 'overwriting previous {} result of {} for the {}/{} session:'
                            ' {} ==> {}'.format(course_code, mat_no, session_taken, session_taken + 1, old, score))

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
        previous_categories = [x['category'] for x in res_poll if x and x['category'] and x['session'] < session_taken]
        result_record[
            'category'] = 'E' if 'C' in previous_categories else 'D'  # todo test this for when it should be 'D'
    else:
        results_object = deepcopy(result_record)
        mat_no = results_object.pop('mat_no')
        session_taken = results_object.pop('session')
        result_level = results_object.pop('level')
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
            # todo: optimise this by initialising a dictionary outside the main loop... course_code : course_credit
            #       add every unique course query here
            #       search this dict first for the course credit
            #       ...Next release of course
            #       .
            #  NEW: since it's per-level this would work out really well
            #       only update dict for carryovers
            #       dict should be IN FUNCTION but OUTSIDE LOOP
            #
            credit = course_details.get(course, 0)['course_credit']
            crs_grade = [x[1] for x in result_courses if x[0] == course]
            if crs_grade and crs_grade[0] not in ['F', 'ABS']:
                credits_passed += credit
            total_credits += credit
        result_record['category'] = utils.compute_category(mat_no, result_level, session_taken, total_credits,
                                                           credits_passed)

    res_record = result_xxx_schema.load(result_record)
    # db_session = scoped_session(sessionmaker(bind=db.get_engine(app, db_name.replace("_", "-"))))
    db_session = result_xxx_schema.Meta.sqla_session
    db_session.add(res_record)
    db_session.commit()

    if not is_unusual:
        gpa_credits = list(zip(*utils.get_gpa_credits(mat_no)))
        index = (result_level // 100 - 1)
        level_gpa = gpa_credits[index][0] if gpa_credits[index][0] else 0
        level_credits_passed = gpa_credits[index][1] if gpa_credits[index][1] else 0

        if grade != previous_entry_grade:
            course_credit = course_details.get(course_code, 0)['course_credit']
            creds = utils.get_credits(mat_no)
            # ensure to get the right value irrespective of the size of the list (PUTME vs DE students)
            level_credits = creds[index + (len(creds) - 5)]
            grading_point_rule = utils.get_grading_point(mat_no)
            grading_point = int(grading_point_rule[grade])
            grading_point_old = int(grading_point_rule[previous_entry_grade]) if previous_entry_grade else 0

            level_gpa = level_gpa + ((course_credit * (grading_point - grading_point_old)) / level_credits)
            level_credits_passed += course_credit

        gpa_credits[index] = (round(level_gpa, 4), level_credits_passed)
        for ind in range(len(gpa_credits)):
            if gpa_credits[ind][0]:
                gpa_credits[ind] = str(gpa_credits[ind][0]), str(gpa_credits[ind][1])
            else:
                gpa_credits[ind] = None, None
        gpa_credits = {'mat_no': mat_no,
                       'level100': ','.join(gpa_credits[0]) if gpa_credits[0][0] else None,
                       'level200': ','.join(gpa_credits[1]) if gpa_credits[1][0] else None,
                       'level300': ','.join(gpa_credits[2]) if gpa_credits[2][0] else None,
                       'level400': ','.join(gpa_credits[3]) if gpa_credits[3][0] else None,
                       'level500': ','.join(gpa_credits[4]) if gpa_credits[4][0] else None}

        gpa_record = session.GPACreditsSchema().load(gpa_credits)
        db_session.add(gpa_record)
        db_session.commit()
        db_session.close()
        return error_log, 201

    return error_log, 400


# =========================================================================================
#                                   Utility functions
# =========================================================================================

def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    iters = sorted(iters, key=lambda x: x[0][3])
    return sorted(iters, key=lambda x: x[3])


def get_table_to_populate(session_course_reg, full_res_poll):
    result_level = session_course_reg['course_reg_level']
    # selecting Result table for a fresh input (first result entered for the student for the session)
    if session_course_reg['courses'] and not full_res_poll[int(session_course_reg['table'][-3:]) // 100 - 1]:
        # use table corresponding to course reg table if it is available
        table_to_populate = 'Result' + session_course_reg['table'][-3:]
    elif not full_res_poll[result_level // 100 - 1]:
        table_to_populate = 'Result' + str(result_level)
    else:
        table_to_populate = 'Result' + str(100 * ([ind for ind, result in enumerate(full_res_poll) if not result][0] + 1))
    return table_to_populate
