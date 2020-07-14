import os.path
from sms import utils
from sms import course_details
from sms.config import db
from sms.users import access_decorator
from copy import deepcopy


@access_decorator
def post(list_of_results):
    """  ==== JSON FORMAT FOR THE RESULTS ====

    res = [
              ['MEE351', '2019', 'ENG1503886', '98'],['MEE451', '2019', 'ENG1503886', '98'],
              ['EMA481', '2019', 'ENG1503886', '98'],['MEE561', '2019', 'ENG1503886', '98'],
              ['MEE571', '2019', 'ENG1503886', '98'],['MEE521', '2019', 'ENG1503886', '98'],
              ['MEE572', '2019', 'ENG1503886', '98'],
          ]
    """

    base_dir = os.path.dirname(__file__)
    result_errors = open(os.path.join(base_dir, 'result_errors.txt'), 'a')
    error_log = []

    for index, result_details in enumerate(list_of_results):
        course_code, session_taken, mat_no, score = result_details
        session_taken, score = map(int, [session_taken, score])
        grade = utils.compute_grade(mat_no, score, ignore_404=True)

        # Error check on grade and score
        if not grade:
            error_log.append('{0} at index {1} was not found in the database'.format(mat_no, index))
            print('\n====>>  ', error_log[-1])
            continue
        if not (0 <= score <= 100):
            error_text = "Unexpected value for score, '{}', for {} at index {}; " \
                         "result not added".format(score, mat_no, index)
            # todo: extend this to include user, datetime, etc.
            result_errors.writelines(str(result_details) + '  error: ' + error_text + '\n')
            error_log.append(error_text)
            print('\n====>>  ', error_log[-1])
            continue

        is_unusual = False
        previous_entry_grade = ''  # for updating GPA value
        is_first = False

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
                             '{2}/{3} session'.format(mat_no, index, session_taken, session_taken+1))
            print('\n====>>  ', error_log[-1])

        courses_registered = course_registration['courses']
        if not is_unusual and course_code not in courses_registered:
            is_unusual = True
            error_log.append('{0} at index {1} did not register {2} in the {3}/{4} '
                             'session'.format(mat_no, index, course_code, session_taken, session_taken+1))
            print('\n====>>  ', error_log[-1])

        db_name = utils.get_DB(mat_no)[:-3]
        session = utils.load_session(db_name)
        result_level = course_registration['course_reg_level']
        res = utils.result_poll(mat_no)
        result_record = {}
        table_to_populate = ''

        for idx, result in enumerate(res):
            if result and result['session'] == session_taken:
                result_record = result
                table_to_populate = 'Result' + str((idx + 1) * 100)
                break
        if not result_record:
            # selecting Result table for a fresh input (first result entered for the student for the session)
            is_first = True
            if courses_registered: table_to_populate = 'Result' + course_registration['table'][-3:]
            elif res[result_level//100 - 1] == {}: table_to_populate = 'Result' + str(result_level)
            else:
                table_to_populate = 'Result' + str(100 * ([ind for ind, result in enumerate(res) if not result][0] + 1))

            # preparing the new table
            table_columns = utils.get_attribute_names(eval('session.{}'.format(table_to_populate)))
            result_record = {'mat_no': mat_no, 'session': session_taken, 'level': result_level, 'category': None,
                             'carryovers': '', 'unusual_results': ''}
            for col in table_columns:
                if col not in result_record:
                    result_record[col] = None

        # Check if a previous entry for the course exists for session
        if not is_unusual and result_record['unusual_results'] and course_code in result_record['unusual_results']:
            print('\n====>>  ', 'moving result record {} for {} from store to result table'.format(course_code, mat_no))
        elif (course_code in result_record and result_record[course_code]) or (course_code in result_record['carryovers']) or (course_code in result_record['unusual_results']):
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
                  ' {} ==> {}'.format(course_code, mat_no, session_taken, session_taken+1, old, score))

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
            previous_categories = [x['category'] for x in res if x and x['category'] and x['session'] < session_taken]
            result_record['category'] = 'E' if 'C' in previous_categories else 'D' #todo test this for when it should be 'D'
        else:
            results_object = deepcopy(result_record)
            mat_no = results_object.pop('mat_no')
            session_taken = results_object.pop('session')
            result_level = results_object.pop('level')
            carryovers = results_object.pop('carryovers')
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
                credit = course_details.get(course, 0)['course_credit']
                crs_grade = [x[1] for x in result_courses if x[0] == course]
                if crs_grade and crs_grade[0] not in ['F', 'ABS']:
                    credits_passed += credit
                total_credits += credit
            result_record['category'] = utils.compute_category(mat_no, result_level, session_taken, total_credits, credits_passed)

        res_record = eval('session.{}Schema().load(result_record)'.format(table_to_populate))
        db.session.add(res_record)
        db.session.commit()

        if not is_unusual:
            gpa_credits = list(zip(*utils.get_gpa_credits(mat_no)))
            index = result_level // 100 - 1
            level_gpa = gpa_credits[index][0] if gpa_credits[index][0] else 0
            level_credits_passed = gpa_credits[index][1] if gpa_credits[index][1] else 0

            if grade != previous_entry_grade:
                course_credit = course_details.get(course_code, 0)['course_credit']
                level_credits = utils.get_credits(mat_no)[index]
                grading_point_rule = utils.get_grading_point(mat_no)
                grading_point = int(grading_point_rule[grade])
                grading_point_old = int(grading_point_rule[previous_entry_grade]) if previous_entry_grade else 0

                level_gpa = level_gpa + ((course_credit * (grading_point - grading_point_old)) / level_credits)
                level_credits_passed += course_credit

            gpa_credits[index] = (round(level_gpa, 4), level_credits_passed)
            for ind in range(len(gpa_credits)):
                if gpa_credits[ind][0]: gpa_credits[ind] = str(gpa_credits[ind][0]), str(gpa_credits[ind][1])
                else:  gpa_credits[ind] = None, None
            gpa_credits = {'mat_no': mat_no,
                           'level100': ','.join(gpa_credits[0]) if gpa_credits[0][0] else None,
                           'level200': ','.join(gpa_credits[1]) if gpa_credits[1][0] else None,
                           'level300': ','.join(gpa_credits[2]) if gpa_credits[2][0] else None,
                           'level400': ','.join(gpa_credits[3]) if gpa_credits[3][0] else None,
                           'level500': ','.join(gpa_credits[4]) if gpa_credits[4][0] else None}

            gpa_record = session.GPACreditsSchema().load(gpa_credits)
            db.session.add(gpa_record)
            db.session.commit()
            db.session.close()

    result_errors.close()
    print('\n====>>  ', '{} result entries added with {} errors'.format(len(list_of_results), len(error_log)))
    return error_log


@access_decorator
def get(mat_no, acad_session):
    res = utils.result_poll(mat_no)
    results = {}
    table_to_populate = ''
    for index, result in enumerate(res):
        if result and result['session'] == acad_session:
            results = result
            table_to_populate = 'Result' + str((index+1) * 100)
            break
    if results == {}:
        return 'No result available for entered session', 404

    frame = {'table_to_populate': table_to_populate}
    results.pop('mat_no')
    results.pop('category')
    results.pop('session')
    total_credits_passed = results.pop('tcp')
    result_level = results.pop('level')
    carryovers = results.pop('carryovers')
    unusual_results = results.pop('unusual_results')
    all_courses = [[x] + results[x].split(',') for x in results if results[x]]

    if carryovers or unusual_results:
        carryovers = carryovers.split(',') if carryovers else []
        carryovers.extend(unusual_results.split(',') if unusual_results else [])
        carryovers = [x.split(' ') for x in carryovers if carryovers]
        all_courses.extend(carryovers)

    # check if anything in course_reg is not in results... and vice versa
    course_reg = utils.get_registered_courses(mat_no)
    for reg in course_reg:
        if course_reg[reg]['courses'] and course_reg[reg]['course_reg_session'] == acad_session:
            course_reg = course_reg[reg]['courses']
            break
    reg_extras = [[x, '', '', 0, 0, 'Registered, no result'] for x in set(course_reg).difference(set(list(zip(*all_courses))[0]))]
    res_extras = [[x, '', '', 0, 0, 'Course not registered'] for x in set(list(zip(*all_courses))[0]).difference(set(course_reg))]
    for index in range(len(res_extras)):
        for x in range(len(all_courses)):
            if all_courses[x][0] == res_extras[index][0]:
                res_extras[index][1:3] = all_courses[x][1:3]
                del all_courses[x]
                break

    all_courses.extend(reg_extras)
    all_courses.extend(res_extras)
    for index in range(len(all_courses)):
        course_dets = course_details.get(all_courses[index][0], 0)
        if len(all_courses[index]) == 5:
            all_courses[index][3] = course_dets['course_credit']
            all_courses[index][4] = course_dets['course_semester']
        else:
            all_courses[index].extend([course_dets['course_credit'], course_dets['course_semester'], ''])
    frame['level_written'] = result_level
    frame['session_written'] = acad_session
    frame['mat_no'] = mat_no
    frame['courses'] = multisort(all_courses)
    return frame


def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    iters = sorted(iters, key=lambda x: x[0][3])
    return sorted(iters, key=lambda x: x[3])


