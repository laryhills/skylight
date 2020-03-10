from json import loads
from flask import abort
from sms.config import db
from sms import personal_info
from sms import utils
from sms.utils import get_carryovers
from sms.users import access_decorator


@access_decorator
def get(mat_no, acad_session=None):
    # for new registrations, the assumption is that the level has been updated by admin
    current_level = utils.get_level(mat_no)
    current_session = utils.get_current_session()
    if not acad_session:
        acad_session = current_session
    depat = utils.get_depat('long')

    person = personal_info.get(mat_no, 0)
    phone_no = person['phone_no'] if person['phone_no'] else None
    mode_of_entry = ["PUTME", "DE(200)", "DE(300)"][person["mode_of_entry"] - 1]
    entry_session = person['session_admitted']
    graduation_status = int(person['grad_stats']) if person['grad_stats'] else None
    sex = ['Female', 'Male'][person['sex'] == 'M']
    if person["sex"] == 'F':
        person['surname'] += " (Miss)"

    course_reg_frame = {}
    some_personal_info = {'surname': person['surname'],
                          'othernames': person['othernames'].upper(),
                          'depat': depat,
                          'mode_of_entry': mode_of_entry,
                          'current_level': str(current_level),
                          'phone_no': phone_no,
                          'sex': sex,
                          'email': person['email_address'],
                          'state_of_origin': person['state_of_origin'],
                          'lga_of_origin': person['lga'] if 'lga' in person else ''}

    mode_of_entry = person["mode_of_entry"]

    # use last course_reg table to account for temp withdrawals
    # these guys break any computation that relies on sessions
    course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
    probation_status = None
    fees_status = None
    others = None

    res = [x for x in utils.result_poll(mat_no) if x]
    category = res[-1]["category"] if res and res[-1]["category"] else ''
    if category == 'C':
        probation_status = 1
    elif category in 'AB':
        probation_status = 0

    table_to_populate = ''
    for key in range(100, 900, 100):
        if not course_reg[key]['courses']:
            table_to_populate = course_reg[key]['table']
            break

    error_text = ''
    if graduation_status == 1 if graduation_status else False:
        error_text = 'Student cannot carry out course reg as he has graduated'
    elif int(table_to_populate[-3:]) + 100 > 800:
        error_text = 'Student cannot carry out course reg as he has exceeded the 8-year limit'
    elif category not in 'ABC':
        error_text = 'Student cannot carry out course reg as his category is {}'.format(category)

    table_to_get = ''
    course_registration = {}
    get_new_registration = False
    for reg in course_reg:
        if course_reg[reg]['courses'] and course_reg[reg]['course_reg_session'] == acad_session:
            table_to_get = course_reg[reg]['table']
            course_registration = course_reg[reg]
            break

    if table_to_get == '':
        if acad_session != current_session:
            error_text = 'No course registration for entered session'
        elif acad_session == current_session:
            table_to_get = table_to_populate
            get_new_registration = True

    if error_text != '':
        course_reg_frame = {'personal_info': some_personal_info,
                            'table_to_populate': None,
                            'course_reg_session': current_session,
                            'course_reg_level': None,
                            'level_max_credits': None,
                            'courses': {'first_sem': [],
                                        'second_sem': []},
                            'choices': {'first_sem': [],
                                        'second_sem': []},
                            'probation_status': None,
                            'fees_status': fees_status,
                            'others': others,
                            'error': error_text}
        return error_text, 403

    elif get_new_registration:
        courses = loads(get_carryovers(mat_no))
        first_sem = courses['first_sem']
        if first_sem:
            first_sem_carryover_courses, first_sem_carryover_credits = list(zip(*first_sem))
        else:
            first_sem_carryover_courses, first_sem_carryover_credits = [], []

        second_sem = courses['second_sem']
        if second_sem:
            second_sem_carryover_courses, second_sem_carryover_credits = list(zip(*second_sem))
        else:
            second_sem_carryover_courses, second_sem_carryover_credits = [], []
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
            for crs, title, credit in first_sem_choices:
                credit_sum += credit
            for crs, title, credit in second_sem_choices:
                credit_sum += credit
            if credit_sum == 51:
                level_max_credits = utils.get_maximum_credits_course_reg()['clause_of_51']

        # Handle any case where carryover course credits exceeds the limit
        credit_sum = sum(map(int, first_sem_carryover_credits)) + sum(map(int, second_sem_carryover_credits))
        if credit_sum > level_max_credits or len(first_sem_carry_courses) > 12 or len(second_sem_carry_courses) > 12:
            # dump everything to choices
            first_sem_choices.extend(first_sem_carry_courses)
            second_sem_choices.extend(second_sem_carry_courses)
            first_sem_carry_courses, second_sem_carry_courses = [], []

        course_reg_frame = {'personal_info': some_personal_info,
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
                            'others': others,
                            'error': None}

    elif not get_new_registration:
        # getting old course registrations
        course_reg_level   = course_registration['course_reg_level']
        course_reg_session = course_registration['course_reg_session']
        table_to_get       = course_registration['table']
        courses_registered = course_registration['courses']
        probation_status   = course_registration['probation'] if 'probation' in course_registration else None
        fees_status        = course_registration['fees_status'] if 'fees_status' in course_registration else None
        others             = course_registration['others'] if 'others' in course_registration else None

        courses = [[], []]  # first_sem, second_sem
        for course_code in courses_registered:
            course_dets = utils.course_details.get(course_code, 0)
            courses[course_dets['course_semester']-1].append((course_code, course_dets['course_title'], course_dets['course_credit']))
        first_sem = courses[0]
        second_sem = courses[1]

        course_reg_frame = {'personal_info': some_personal_info,
                            'table_to_populate': table_to_get,
                            'course_reg_session': course_reg_session,
                            'course_reg_level': course_reg_level,
                            'max_credits': None,
                            'courses': {'first_sem': multisort(first_sem),
                                        'second_sem': multisort(second_sem)},
                            'choices': {'first_sem': [],
                                        'second_sem': []},
                            'probation_status': probation_status,
                            'fees_status': fees_status,
                            'others': others,
                            'error': None}
    return course_reg_frame


@access_decorator
def post(course_reg):
    # The 'session_acad' variable is to enable edits

    """ ======= FORMAT =======
        mat_no: 'ENGxxxxxxx'
        table_to_populate: 'CourseRegxxx'
        course_reg_session = 20xx
        course_reg_level = x00
        max_credits: <int>
        courses:
            first_sem: ['course_code1', 'course_code2', ...]
            second_sem: []
        probation_status: <int>
        fees_status: <int>
        others: ''
        =======================

    example...
    c_reg = {'mat_no': 'ENG1503886', 'table_to_populate': 'CourseReg500', 'course_reg_session': 2019, 'course_reg_level': 500, 'max_credits': 50, 'courses': {'first_sem': ['MEE521', 'MEE451', 'MEE561', 'MEE571', 'EMA481', 'MEE502'], 'second_sem': []}, 'probation_status': 0, 'fees_status': None, 'others': None}
    """

    courses = []
    courses.extend(course_reg['courses']['first_sem'])
    courses.extend(course_reg['courses']['second_sem'])
    courses = sorted(courses)

    mat_no             = course_reg['mat_no']
    table_to_populate  = course_reg['table_to_populate']
    course_reg_session = course_reg['course_reg_session']
    course_reg_level   = course_reg['course_reg_level']
    fees_status        = course_reg['fees_status']
    probation          = course_reg['probation_status']
    others             = course_reg['others']

    db_name = utils.get_DB(mat_no)[:-3]
    session = utils.load_session(db_name)

    try:
        exec('from sms.models._{0} import {1}Schema'.format(db_name, table_to_populate))
        exec('from sms.models._{0} import {1}'.format(db_name, table_to_populate))
    except ImportError:
        abort(400)

    CourseRegxxxSchema = locals()[table_to_populate+'Schema']
    CourseRegxxx = locals()[table_to_populate]

    table_columns = utils.get_attribute_names(CourseRegxxx)
    registration = {}
    for col in table_columns:
        if col in courses:
            registration[col] = '1'
            courses.remove(col)
        elif col not in ['mat_no', 'carryovers', 'probation', 'others','fees_status', 'level', 'session']:
            registration[col] = '0'
    registration['carryovers'] = ','.join(courses)
    registration['mat_no'] = mat_no
    registration['probation'] = probation
    registration['others'] = others
    registration['fees_status'] = fees_status
    registration['level'] = course_reg_level
    registration['session'] = course_reg_session

    course_reg_xxx_schema = CourseRegxxxSchema()
    course_registration = course_reg_xxx_schema.load(registration)
    db.session.add(course_registration)
    db.session.commit()
    return 'course registration successful'


def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    return sorted(iters, key=lambda x: x[0][3])
