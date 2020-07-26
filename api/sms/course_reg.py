""" ======= COURSE_REG FORMAT =======
    mat_no: 'ENGxxxxxxx'
    personal_info: {...}
    table_to_populate: 'CourseRegxxx'
    course_reg_session: 20xx
    course_reg_level: x00
    max_credits: <int>
    courses: {
               first_sem: [ ('course_code_1', 'course_title_1', 'course_credits_1'),
                            ('course_code_2', 'course_title_2', 'course_credits_2'), ...]
               second_sem: []
             }
    choices: {
               first_sem: [ ('course_code_1', 'course_title_1', 'course_credits_1'),
                            ('course_code_2', 'course_title_2', 'course_credits_2'), ...]
               second_sem: []
             }
    probation_status: <int>
    fees_status: <int>
    others: ''
    =======================

example...
c_reg = {'mat_no': 'ENG1503886', personal_info: {}, 'table_to_populate': 'CourseReg500', 'course_reg_session': 2019, 'course_reg_level': 500, 'max_credits': 50, 'courses': {'first_sem': ['MEE521', 'MEE451', 'MEE561', 'MEE571', 'EMA481', 'MEE502'], 'second_sem': []}, 'probation_status': 0, 'fees_status': None, 'others': None}
"""
from sms import utils
from sms import results
from sms import course_reg_utils
from sms.users import access_decorator
from sms.config import db


@access_decorator
def init_new(mat_no, acad_session=utils.get_current_session()):
    current_session = utils.get_current_session()
    if acad_session != current_session:
        return 'You do not have authorization to perform course registration outside the current session', 401

    check = check_registration_eligibility(mat_no, acad_session)
    if check[1] != 200:
        return check
    else:
        return init_new_course_reg(*check[0])


@access_decorator
def get(mat_no, acad_session):
    current_session = utils.get_current_session()
    if acad_session != current_session:
        print('Elevated access to course_reg.get_new granted')

    obj = get_existing_course_reg(mat_no, acad_session)
    if obj[1] != 200:
        return obj
    old_course_reg = obj[0]
    old_course_reg['max_credits'] = utils.get_maximum_credits_for_course_reg()['normal']
    return old_course_reg, 200


@access_decorator
def post(data):
    current_session = utils.get_current_session()
    if data['course_reg_session'] != current_session:
        return 'You do not have authorization to perform course registration outside the current session', 401
    return post_course_reg(data)


@access_decorator
def put(data):
    print('Elevated course_reg write access granted')
    return post_course_reg(data)


def check_registration_eligibility(mat_no, acad_session):
    current_level = utils.get_level(mat_no)
    res_poll = utils.result_poll(mat_no)
    course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
    s_personal_info = course_reg_utils.process_personal_info(mat_no)
    table_to_populate = course_reg_utils.get_table_to_populate(current_level, acad_session, res_poll, course_reg)
    probation_status, previous_category = course_reg_utils.get_probation_status_and_prev_category(res_poll, acad_session)
    graduation_status = s_personal_info['grad_stats']

    # handle special cases
    error_text = ''
    if graduation_status and graduation_status == 1:
        error_text = 'Student cannot carry out course reg as he has graduated'
    elif table_to_populate == '':   # or int(table_to_populate[-3:]) + 100 > 800
        error_text = 'Student cannot carry out course reg as he has exceeded the 8-year limit'
    elif previous_category not in 'ABC':
        error_text = 'Student cannot carry out course reg as his category is {}'.format(previous_category)
    if error_text != '':
        return error_text, 403

    ret_obj = (mat_no, acad_session, table_to_populate, probation_status, s_personal_info)
    return ret_obj, 200


def init_new_course_reg(mat_no, acad_session, table_to_populate, probation_status, s_personal_info):
    current_level = utils.get_level(mat_no)
    first_sem_carryover_courses, second_sem_carryover_courses = course_reg_utils.fetch_carryovers(mat_no, current_level)
    mode_of_entry = s_personal_info.pop('mode_of_entry_numeric')
    # populating choices
    try:
        index = (int(current_level) // 100) - 1
    except Exception as e:
        print(e)
        return 'Cannot determine current level of student', 400

    level_courses = utils.get_courses(mat_no, mode_of_entry)
    fields = ['course_code', 'course_title', 'course_credit']
    first_sem_choices = course_reg_utils.enrich_course_list(level_courses[index][0], fields=fields)
    second_sem_choices = course_reg_utils.enrich_course_list(level_courses[index][1], fields=fields)
    first_sem_carryover_courses = course_reg_utils.enrich_course_list(first_sem_carryover_courses, fields=fields)
    second_sem_carryover_courses = course_reg_utils.enrich_course_list(second_sem_carryover_courses, fields=fields)

    # Getting maximum possible credits to register
    level_max_credits = utils.get_maximum_credits_for_course_reg()['normal']

    # Handle any case where carryover course credits exceeds the limit
    credit_sum = course_reg_utils.sum_credits_many(first_sem_carryover_courses, second_sem_carryover_courses,
                                                   index_for_credits=2)
    if credit_sum > level_max_credits or max(len(first_sem_carryover_courses), len(second_sem_carryover_courses)) > 12:
        # dump everything to choices
        first_sem_choices.extend(first_sem_carryover_courses)
        second_sem_choices.extend(second_sem_carryover_courses)
        first_sem_carryover_courses, second_sem_carryover_courses = [], []

    # Implementing the "clause of 51"
    if current_level >= 500:
        credit_sum += course_reg_utils.sum_credits_many(first_sem_choices, second_sem_choices, index_for_credits=2)
        if credit_sum == utils.get_maximum_credits_for_course_reg()['clause_of_51']:
            level_max_credits = utils.get_maximum_credits_for_course_reg()['clause_of_51']

    course_reg_frame = {'mat_no': mat_no,
                        'personal_info': s_personal_info,
                        'table_to_populate': table_to_populate,
                        'course_reg_session': acad_session,
                        'course_reg_level': current_level,
                        'max_credits': level_max_credits,
                        'courses': {'first_sem': course_reg_utils.multisort(first_sem_carryover_courses),
                                    'second_sem': course_reg_utils.multisort(second_sem_carryover_courses)},
                        'choices': {'first_sem': course_reg_utils.multisort(first_sem_choices),
                                    'second_sem': course_reg_utils.multisort(second_sem_choices)},
                        'probation_status': probation_status,
                        'fees_status': 0,
                        'others': ''}
    return course_reg_frame, 200


def get_existing_course_reg(mat_no, acad_session, old_course_reg=None, s_personal_info=None):
    if not s_personal_info: s_personal_info = course_reg_utils.process_personal_info(mat_no)
    if not old_course_reg:
        course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
        old_course_reg = course_reg_utils.get_course_reg_at_acad_session(acad_session, course_reg)

    if old_course_reg == {}:
        return 'No course registration for entered session', 404

    fields = ('course_code', 'course_title', 'course_credit', 'course_semester')
    courses_registered = course_reg_utils.enrich_course_list(old_course_reg['courses'], fields=fields)
    courses = [[], []]  # first_sem, second_sem
    [courses[course.pop(3) - 1].append(course) for course in courses_registered]

    course_reg_frame = {'mat_no': mat_no,
                        'personal_info': s_personal_info,
                        'table_to_populate': old_course_reg['table'],
                        'course_reg_session': old_course_reg['course_reg_session'],
                        'course_reg_level': old_course_reg['course_reg_level'],
                        'max_credits': '',
                        'courses': {'first_sem': course_reg_utils.multisort(courses[0]),
                                    'second_sem': course_reg_utils.multisort(courses[1])},
                        'choices': {'first_sem': [],
                                    'second_sem': []},
                        'probation_status': old_course_reg['probation'],
                        'fees_status': old_course_reg['fees_status'],
                        'others': old_course_reg['others']}
    return course_reg_frame, 200


def post_course_reg(data):
    courses = []
    tcr = [0, 0]
    for idx, sem in enumerate(['first_sem', 'second_sem']):
        for course_obj in data['courses'][sem]:
            courses.append(course_obj[0])
            tcr[idx] += course_obj[2]
    courses = sorted(courses)
    mat_no = data['mat_no']
    table_to_populate = data['table_to_populate']
    course_reg_session = data['course_reg_session']

    db_name = utils.get_DB(mat_no)[:-3]
    if not db_name:
        return 'Student not found in database', 403
    session = utils.load_session(db_name)

    try:
        course_reg_xxx_schema = eval('session.{}Schema()'.format(table_to_populate))
    except ImportError:
        return '{} table does not exist'.format(table_to_populate), 403

    table_columns = course_reg_xxx_schema.load_fields.keys()
    registration = {}
    for col in table_columns:
        if col in courses:
            registration[col] = '1'
            courses.remove(col)
        elif col not in ['carryovers', 'mat_no', 'tcr', 'level', 'session', 'probation', 'fees_status', 'others']:
            registration[col] = '0'
    registration['carryovers'] = ','.join(courses)
    registration['mat_no'] = mat_no
    registration['tcr'] = sum(tcr)
    registration['level'] = data['course_reg_level']
    registration['session'] = course_reg_session
    registration['probation'] = data['probation_status']
    registration['fees_status'] = data['fees_status']
    registration['others'] = data['others']

    course_registration = course_reg_xxx_schema.load(registration)
    db.session.add(course_registration)
    db.session.commit()

    # Here we check if there were any stray results waiting in unusual results for this session
    session_results = [x for x in utils.result_poll(mat_no) if x and (x['session'] == course_reg_session)]
    if session_results and 'unusual_results' in session_results[0] and session_results[0]['unusual_results']:
        unusual_results = session_results[0]['unusual_results'].split(',')
        unusual_results = [[x.split(' ')[0], course_reg_session, mat_no, x.split(' ')[1]] for x in unusual_results]
        results.post(unusual_results)

    print('\n====>>  ', 'course registration successful')
    return 'course registration successful', 201
