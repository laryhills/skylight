from json import loads
from sms import utils
from sms import results
from sms import personal_info
from sms import course_details
from sms.utils import get_carryovers
from sms.users import access_decorator
from sms.config import db



@access_decorator
def get(mat_no, acad_session=None):
    # for new registrations, the assumption is that the level has been updated by admin
    current_session = utils.get_current_session()
    if not acad_session:
        acad_session = current_session

    some_personal_info = personal_info.get(mat_no, 0)
    current_level = some_personal_info['current_level']
    mode_of_entry = some_personal_info["mode_of_entry"]
    graduation_status = int(some_personal_info['grad_stats']) if some_personal_info['grad_stats'] else ''

    some_personal_info["mode_of_entry"] = ["PUTME", "DE(200)", "DE(300)"][some_personal_info["mode_of_entry"] - 1]
    some_personal_info['department'] = utils.get_depat('long')
    for key in some_personal_info:
        if not some_personal_info[key]:
            some_personal_info[key] = ''
    if some_personal_info["sex"] == 'F':
        some_personal_info['surname'] += " (Miss)"

    course_reg_frame = {}

    # use last course_reg table to account for temp withdrawals
    # these guys break any computation that relies on sessions
    course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
    probation_status = 0
    fees_status = 0
    others = ''

    res_poll = utils.result_poll(mat_no)
    previous_categories = [x['category'] for x in res_poll if x and x['category'] and x['session'] < acad_session]
    previous_category = previous_categories[-1] if len(previous_categories) > 0 else ''
    if previous_category == 'C':
        probation_status = 1

    table_to_populate = ''
    index = [ind for ind, x in enumerate(res_poll) if x and x['session'] == acad_session]
    if index: table_to_populate = 'CourseReg' + str(100 * (index[0]+1))
    elif not course_reg[current_level]['courses']: table_to_populate = course_reg[current_level]['table']
    else:
        for key in range(100, 900, 100):
            if not course_reg[key]['courses']:
                table_to_populate = course_reg[key]['table']
                break

    error_text = ''
    if graduation_status == 1 if graduation_status else False:
        error_text = 'Student cannot carry out course reg as he has graduated'
    elif int(table_to_populate[-3:]) + 100 > 800 or table_to_populate == '':
        error_text = 'Student cannot carry out course reg as he has exceeded the 8-year limit'
    elif previous_category not in 'ABC':
        error_text = 'Student cannot carry out course reg as his category is {}'.format(previous_category)

    course_registration = {}
    get_new_registration = False
    for reg in course_reg:
        if course_reg[reg]['courses'] and course_reg[reg]['course_reg_session'] == acad_session:
            course_registration = course_reg[reg]
            break

    if course_registration == {}:
        if acad_session != current_session:
            error_text = 'No course registration for entered session'
        elif acad_session == current_session:
            get_new_registration = True

    if error_text != '':
        return error_text, 403

    elif get_new_registration:
        courses = loads(get_carryovers(mat_no))
        first_sem = courses['first_sem']
        if first_sem: first_sem_carryover_courses, first_sem_carryover_credits = list(zip(*first_sem))
        else: first_sem_carryover_courses, first_sem_carryover_credits = [], []

        second_sem = courses['second_sem']
        if second_sem: second_sem_carryover_courses, second_sem_carryover_credits = list(zip(*second_sem))
        else: second_sem_carryover_courses, second_sem_carryover_credits = [], []

        if current_level == 400:
            # Force only reg of UBITS for incoming 400L
            second_sem_carryover_courses, second_sem_carryover_credits = ["UBT400"], ["6"]
        elif current_level == 500:
            if "UBT400" in second_sem_carryover_courses:
                second_sem_carryover_courses = list(second_sem_carryover_courses)
                second_sem_carryover_credits = list(second_sem_carryover_credits)
                second_sem_carryover_courses.remove("UBT400")
                second_sem_carryover_credits.remove("6")

        first_sem_carry_courses, second_sem_carry_courses = [], []
        for index in range(len(first_sem_carryover_courses)):
            crse_dets = utils.course_details.get(first_sem_carryover_courses[index], 0)
            first_sem_carry_courses.append((first_sem_carryover_courses[index], crse_dets['course_title'], int(first_sem_carryover_credits[index])))
        for index in range(len(second_sem_carryover_courses)):
            crse_dets = utils.course_details.get(second_sem_carryover_courses[index], 0)
            second_sem_carry_courses.append((second_sem_carryover_courses[index], crse_dets['course_title'], int(second_sem_carryover_credits[index])))

        # populating choices
        courses = utils.get_courses(mat_no, mode_of_entry)
        index = (current_level // 100) - 1 if current_level != 0 else -99
        first_sem_choices, second_sem_choices = [], []
        for crse in courses[index][0]:
            if crse not in first_sem_carryover_courses:
                crse_dets = utils.course_details.get(crse, 0)
                first_sem_choices.append((crse, crse_dets['course_title'], crse_dets['course_credit']))
        for crse in courses[index][1]:
            if crse not in second_sem_carryover_courses:
                crse_dets = utils.course_details.get(crse, 0)
                second_sem_choices.append((crse, crse_dets['course_title'], crse_dets['course_credit']))

        # Getting maximum possible credits to register
        level_max_credits = utils.get_maximum_credits_for_course_reg()['normal']

        # Implementing the "clause of 51"
        if current_level >= 500:
            credit_sum = sum(map(int, first_sem_carryover_credits)) + sum(map(int, second_sem_carryover_credits))
            credit_sum += sum([credit for crs, title, credit in first_sem_choices])
            credit_sum += sum([credit for crs, title, credit in second_sem_choices])
            if credit_sum > level_max_credits:
                level_max_credits = utils.get_maximum_credits_for_course_reg()['clause_of_51']

        # Handle any case where carryover course credits exceeds the limit
        credit_sum = sum(map(int, first_sem_carryover_credits)) + sum(map(int, second_sem_carryover_credits))
        if credit_sum > level_max_credits or len(first_sem_carry_courses) > 12 or len(second_sem_carry_courses) > 12:
            # dump everything to choices
            first_sem_choices.extend(first_sem_carry_courses)
            second_sem_choices.extend(second_sem_carry_courses)
            first_sem_carry_courses, second_sem_carry_courses = [], []

        course_reg_frame = {'mat_no': mat_no,
                            'personal_info': some_personal_info,
                            'table_to_populate': table_to_populate,
                            'course_reg_session': current_session,
                            'course_reg_level': current_level,
                            'max_credits': level_max_credits,
                            'courses': {'first_sem': multisort(first_sem_carry_courses),
                                        'second_sem': multisort(second_sem_carry_courses)},
                            'choices': {'first_sem': multisort(first_sem_choices),
                                        'second_sem': multisort(second_sem_choices)},
                            'probation_status': probation_status,
                            'fees_status': fees_status,
                            'others': others}

    elif not get_new_registration:
        # getting old course registrations
        courses_registered = course_registration['courses']
        courses = [[], []]  # first_sem, second_sem
        for course_code in courses_registered:
            course_dets = course_details.get(course_code, 0)
            courses[course_dets['course_semester']-1].append((course_code, course_dets['course_title'], course_dets['course_credit']))
        first_sem = courses[0]
        second_sem = courses[1]

        course_reg_frame = {'mat_no': mat_no,
                            'personal_info': some_personal_info,
                            'table_to_populate': course_registration['table'],
                            'course_reg_session': course_registration['course_reg_session'],
                            'course_reg_level': course_registration['course_reg_level'],
                            'max_credits': '',
                            'courses': {'first_sem': multisort(first_sem),
                                        'second_sem': multisort(second_sem)},
                            'choices': {'first_sem': [],
                                        'second_sem': []},
                            'probation_status': course_registration['probation'],
                            'fees_status': course_registration['fees_status'],
                            'others': course_registration['others']}
    return course_reg_frame


@access_decorator
def post(course_reg):

    """ ======= FORMAT =======
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

    courses = []
    tcr = [0, 0]
    for idx, sem in enumerate(['first_sem', 'second_sem']):
        for course_obj in course_reg['courses'][sem]:
            courses.append(course_obj[0])
            tcr[idx] += course_obj[2]
    courses = sorted(courses)

    mat_no = course_reg['mat_no']
    table_to_populate = course_reg['table_to_populate']
    course_reg_session = course_reg['course_reg_session']
    db_name = utils.get_DB(mat_no)[:-3]
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
        elif col not in ['mat_no', 'carryovers', 'probation', 'others', 'fees_status', 'level', 'session', 'tcr']:
            registration[col] = '0'
    registration['carryovers'] = ','.join(courses)
    registration['mat_no'] = mat_no
    registration['tcr'] = sum(tcr)
    registration['level'] = course_reg['course_reg_level']
    registration['session'] = course_reg_session
    registration['probation'] = course_reg['probation_status']
    registration['fees_status'] = course_reg['fees_status']
    registration['others'] = course_reg['others']

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
    return 'course registration successful'


def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    return sorted(iters, key=lambda x: x[0][3])
