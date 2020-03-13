from flask import abort
from sms.config import db
from sms import utils


def post(list_of_results):
    """  ==== JSON FORMAT FOR THE RESULTS ====
       [['MEE551', '2019', 'ENG1503886', '98'],
        ['MEE561', '2019', 'ENG1503886', '98'],
        ['MEE571', '2019', 'ENG1503886', '98'],
        ['MEE521', '2019', 'ENG1503886', '98']]

        er = [['EMA481', '2019', 'ENG1503886', '98'],['MEE561', '2019', 'ENG1503886', '98'],['MEE571', '2019', 'ENG1503886', '98'],['MEE521', '2019', 'ENG1503886', '98']]
        """

    # List of tuples ==> [(result, error), (result, error)]
    results_with_errors = []

    for index, result_details in enumerate(list_of_results):
        course_code, session_taken, mat_no, score = result_details
        session_taken, score = map(int, [session_taken, score])

        course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
        course_registration = {}
        for key in course_reg:
            if course_reg[key]['course_reg_session'] == session_taken:
                course_registration = course_reg[key]
        if course_registration == {}:
            # todo: add these results to a new column in results table for such errors
            # todo: perhaps this guy's results can only be entered with admin approval
            results_with_errors.append((result_details, 'No course registration found for {0} at index {1} for the '
                                                        '{2}/{3} session'.format(mat_no, index, session_taken,
                                                                                 session_taken+1)))
            print(results_with_errors[-1][1])
            continue
        courses_registered = course_registration['courses']
        if course_code not in courses_registered:
            # todo: add these results to a new column in results table for such errors
            # todo: front end persists the error message encountered in results in memory for each session
            results_with_errors.append((result_details, '{0} at index {1} did not register {2} in the {3}/{4} '
                                                        'session'.format(mat_no, index, course_code, session_taken,
                                                                         session_taken+1)))
            print(results_with_errors[-1][1])
            continue
        else:
            res = utils.result_poll(mat_no)
            result_record = {}
            table_to_populate = ''
            for index, result in enumerate(res):
                if result and result['session'] == session_taken:
                    result_record = result
                    table_to_populate = 'Result' + str((index + 1) * 100)
                    break

            db_name = utils.get_DB(mat_no)[:-3]
            session = utils.load_session(db_name)

            if not result_record:
                table_to_populate = 'Result' + str(100 * ([ind for ind, result in enumerate(res) if not result][0] + 1))
                result_level = course_registration['course_reg_level']
                table_columns = utils.get_attribute_names(eval('session.{}'.format(table_to_populate)))
                result_record = {'mat_no': mat_no, 'session': session_taken, 'level': result_level, 'category': None,
                                 'carryovers': ''}
                for col in table_columns:
                    if col not in result_record:
                        result_record[col] = None

            if (course_code in result_record and result_record[course_code]) or course_code in result_record['carryovers']:
                print('overwriting previous {} result of {} for the {}/{} session'.format(course_code, mat_no, session_taken, session_taken+1))
                # todo add the old and new scores to the error log or sth ...': {old} ==> {new}'

            grading_rules = utils.get_grading_rule(mat_no)
            grade = 'A'

            if course_code in result_record:
                result_record[course_code] = '{},{}'.format(score, grade) # todo get grading rules
            elif course_code in result_record['carryovers']:
                # some pretty hard work here
                pass
            else:
                container = ',{} {} {}' if result_record['carryovers'] else '{} {} {}'
                result_record['carryovers'] += container.format(course_code, score, grade)

            # todo: handle category
            #       * (re)calculate GPAs if results complete... check with course_reg
            #       * recalculate other stuff when done... like category

            res_record = eval('session.{}Schema().load(result_record)'.format(table_to_populate))
            db.session.add(res_record)
            db.session.commit()
    print('result input done with {} errors'.format(len(results_with_errors)))
    return results_with_errors


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
    result_level = results.pop('level')
    carryovers = results.pop('carryovers')
    if carryovers:
        carryovers = carryovers.split(',')
        carryovers = [x.split(' ')[:2] for x in carryovers if carryovers]
    all_courses = [[x, results[x].split(',')[0]] for x in results if results[x]]
    all_courses.extend(carryovers)

    # check if anything in course_reg is not in results... and vice versa
    course_reg = utils.get_registered_courses(mat_no)
    for reg in course_reg:
        if course_reg[reg]['courses'] and course_reg[reg]['course_reg_session'] == acad_session:
            course_reg = course_reg[reg]['courses']
            break
    reg_extras = [[x, '', 0, 'Registered, no result'] for x in set(course_reg).difference(set(list(zip(*all_courses))[0]))]
    res_extras = [[x, '', 0, 'Course not registered'] for x in set(list(zip(*all_courses))[0]).difference(set(course_reg))]
    for index in range(len(res_extras)):
        for x in range(len(all_courses)):
            if all_courses[x][0] == res_extras[index][0]:
                res_extras[index][1] = all_courses[x][1]
                del all_courses[x]
                break

    all_courses.extend(reg_extras)
    all_courses.extend(res_extras)
    for index in range(len(all_courses)):
        course_dets = utils.course_details.get(all_courses[index][0], 0)
        if len(all_courses[index]) == 4:
            all_courses[index][2] = course_dets['course_semester']
        else:
            all_courses[index].extend([course_dets['course_semester'], ''])
    frame['level_written'] = result_level
    frame['session_written'] = acad_session
    frame['mat_no'] = mat_no
    frame['courses'] = multisort(all_courses)
    return frame


def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    iters = sorted(iters, key=lambda x: x[0][3])
    return sorted(iters, key=lambda x: x[2])

# todo revert the changes in test's records: "ENG1508633"
# w = result_input.get('ENG1508633',2018)
