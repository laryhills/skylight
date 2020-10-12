""" ======= COURSE_REG FORMAT =======
    mat_no: 'ENGxxxxxxx'

    personal_info: { ... }

    table_to_populate: 'CourseRegxxx'

    course_reg_session: <int> 20xx

    course_reg_level: <int> x00

    max_credits: <int>

    courses: {
               first_sem: [ ('course_code_1', 'course_title_1', 'course_credits_1', 'course_level_1'),
                            ('course_code_2', 'course_title_2', 'course_credits_2', 'course_level_2'), ...]
               second_sem: [ ... ]
             }
    choices: {
               first_sem: [ ('course_code_1', 'course_title_1', 'course_credits_1', 'course_level_1'),
                            ('course_code_2', 'course_title_2', 'course_credits_2', 'course_level_2'), ...]
               second_sem: [ ... ]
             }
    probation_status: <int>

    fees_status: <int>

    others: ''

    =======================

"""
from sms.src import course_reg_utils, results, utils
from sms.src.users import access_decorator


@access_decorator
def init_new(mat_no):
    return init_new_course_reg(mat_no)


@access_decorator
def get(mat_no, acad_session):
    return get_existing_course_reg(mat_no, acad_session)


@access_decorator
def post(data, superuser=False):
    current_session = utils.get_current_session()
    if not superuser and data['course_reg_session'] != current_session:
        return 'You do not have authorization to perform course registration outside the current session', 401
    return post_course_reg(data)


@access_decorator
def delete(mat_no, acad_session, superuser=False):
    current_session = utils.get_current_session()
    if not superuser and acad_session != current_session:
        return 'You do not have authorization to delete course registration outside the current session', 401
    return delete_course_reg_entry(mat_no, acad_session)


# ==============================================================================================
#                                  Core functions
# ==============================================================================================

def check_registration_eligibility(mat_no, acad_session):
    # does this check for the supplied mat_no in the academic session: acad_session
    current_level = utils.get_level(mat_no)
    res_poll = utils.result_poll(mat_no)
    reg_poll = utils.course_reg_poll(mat_no)

    course_reg_exists = course_reg_utils.course_reg_for_session(mat_no, acad_session, reg_poll)
    if course_reg_exists:
        return 'Course Registration already exists', 403

    s_personal_info = course_reg_utils.process_personal_info(mat_no)
    table_to_populate = course_reg_utils.get_table_to_populate(current_level, acad_session, res_poll, reg_poll)
    probation_status, prev_catg = course_reg_utils.get_probation_status_and_prev_category(res_poll, acad_session)
    graduation_status = s_personal_info['grad_status']

    # handle special cases
    error_text = ''
    if graduation_status and graduation_status == 1:
        error_text = 'Student cannot carry out course reg as he has graduated'
    elif table_to_populate == '':   # or int(table_to_populate[-3:]) + 100 > 800
        error_text = 'Student cannot carry out course reg as he has exceeded the 8-year limit'
    elif prev_catg not in 'ABC':
        error_text = 'Student cannot carry out course reg as his previous category is {}'.format(prev_catg)
    if error_text != '':
        return error_text, 403

    ret_obj = (table_to_populate, current_level, probation_status, s_personal_info)
    return ret_obj, 200


def init_new_course_reg(mat_no):
    # perform some checks
    current_session = utils.get_current_session()
    ret_tuple = check_registration_eligibility(mat_no, current_session)
    if ret_tuple[1] != 200:
        return ret_tuple
    table_to_populate, current_level, probation_status, s_personal_info = ret_tuple[0]

    carryovers = course_reg_utils.fetch_carryovers(mat_no, current_level)
    mode_of_entry = s_personal_info['mode_of_entry']
    index = utils.ltoi(min(int(current_level), 500))

    level_courses = utils.get_courses(mat_no, mode_of_entry)
    options = course_reg_utils.get_optional_courses(current_level)
    # get the optional courses credit sum less one optional course which should be returned in level courses
    abridged_options_credit_sum = course_reg_utils.sum_credits_many(options[0][1:], options[1][1:], credits_index=1)

    # TODO remove any optional course from carryovers and ensure it is in choices
    options = [[crs[0] for crs in options[sem]] for sem in (0, 1)]
    level_courses[index] = [list(set(level_courses[index][sem] + (options[sem]))) for sem in (0, 1)]

    course_lists = [*level_courses[index], *carryovers]
    course_lists = [utils.multisort(course_reg_utils.enrich_course_list(lis)) for lis in course_lists]
    choices, carryovers = course_lists[:2], course_lists[2:]

    # Getting maximum possible credits to register
    level_max_credits = utils.get_max_reg_credits()

    # Handle any case where carryover course credits exceeds the limit
    credit_sum = course_reg_utils.sum_credits_many(*carryovers, credits_index=2)
    if credit_sum > level_max_credits or max(len(carryovers[0]), len(carryovers[1])) > 12:
        # dump everything to choices
        choices = [carryovers[sem] + choices[sem] for sem in (0, 1)]
        carryovers = [[], []]

    # Implementing the "clause of 51"
    if current_level >= 500:
        credit_sum += course_reg_utils.sum_credits_many(*choices, credits_index=2)
        credit_sum -= abridged_options_credit_sum
        conditional_max = utils.get_max_reg_credits(conditional=True)
        if credit_sum == conditional_max:
            level_max_credits = conditional_max

    course_reg_frame = {'mat_no': mat_no,
                        'personal_info': s_personal_info,
                        'table_to_populate': table_to_populate,
                        'course_reg_session': current_session,
                        'course_reg_level': current_level,
                        'max_credits': level_max_credits,
                        'regulars': {'first_sem': choices[0], 'second_sem': choices[1]},
                        'carryovers': {'first_sem': carryovers[0], 'second_sem': carryovers[1]},
                        'probation_status': probation_status,
                        'fees_status': 0,
                        'others': ''}
    return course_reg_frame, 200


def get_existing_course_reg(mat_no, acad_session):
    s_personal_info = course_reg_utils.process_personal_info(mat_no)
    c_reg = course_reg_utils.course_reg_for_session(mat_no, acad_session)
    if not c_reg:
        return 'No course registration for entered session', 404

    fields = ('code', 'title', 'credit', 'semester', 'level')
    courses_regd = utils.multisort(course_reg_utils.enrich_course_list(c_reg['courses'], fields=fields))
    lvl_norm = min(c_reg['level'], 500)
    carryovers, regulars = [[[], []] for _ in range(2)]  # first_sem, second_sem
    [[carryovers, regulars][course[4] == lvl_norm][course.pop(3) - 1].append(course) for course in courses_regd]

    course_reg_frame = {'mat_no': mat_no,
                        'personal_info': s_personal_info,
                        'table_to_populate': c_reg['table'],
                        'course_reg_session': c_reg['session'],
                        'course_reg_level': c_reg['level'],
                        'max_credits': utils.get_max_reg_credits(),
                        'regulars': {'first_sem': regulars[0], 'second_sem': regulars[1]},
                        'carryovers': {'first_sem': carryovers[0], 'second_sem': carryovers[1]},
                        'probation_status': c_reg['probation'],
                        'fees_status': c_reg['fees_status'],
                        'others': c_reg['others']}
    return course_reg_frame, 200


def post_course_reg(data):
    level_options = course_reg_utils.get_optional_courses(data['course_reg_level'])
    level_options = utils.dictify(level_options[0] + level_options[1])
    courses, person_options = [], []
    tcr = [0, 0]
    for idx, sem in enumerate(['first_sem', 'second_sem']):
        for course_obj in data['courses'][sem]:
            courses.append(course_obj[0])
            tcr[idx] += course_obj[2]
            if course_obj[0] in level_options:
                person_options.append('{} {}'.format(idx+1, course_obj[0]))
    courses = sorted(courses)
    mat_no = data['mat_no']
    table_to_populate = data['table_to_populate']
    course_reg_session = data['course_reg_session']

    session = utils.load_session(utils.get_DB(mat_no))
    course_reg_xxx_schema = getattr(session, table_to_populate + 'Schema')()
    table_columns = course_reg_xxx_schema.load_fields.keys()
    registration = {}
    for col in table_columns:
        if col in courses:
            registration[col] = '1'
            courses.remove(col)
        elif col not in ['carryovers', 'mat_no', 'tcr', 'level', 'session', 'probation', 'fees_status', 'others']:
            registration[col] = '0'
    registration.update({
        'carryovers': ','.join(courses),
        'mat_no': mat_no,
        'tcr': sum(tcr),
        'level': data['course_reg_level'],
        'session': course_reg_session,
        'probation': data['probation_status'],
        'fees_status': data['fees_status'],
        'others': data['others']
    })
    course_registration = course_reg_xxx_schema.load(registration)
    db_session = course_reg_xxx_schema.Meta.sqla_session

    if person_options:
        person = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
        person.option = ','.join(person_options)
        db_session.add(person)

    db_session.add(course_registration)
    db_session.commit()
    db_session.close()

    success_text = 'course registration successful'

    # Here we check if there were any stray results waiting in unusual results for this session
    session_results = [x for x in utils.result_poll(mat_no) if x and (x['session'] == course_reg_session)]
    if session_results and ('unusual_results' in session_results[0]) and session_results[0]['unusual_results']:
        unusual_results = [utils.spc_fn(x) for x in utils.csv_fn(session_results[0]['carryovers'])]
        unusual_results = [[x[0], course_reg_session, mat_no, x[1]] for x in unusual_results]
        log = results.add_result_records(unusual_results)

        if log[0]: success_text += '; results for unregistered courses still remain in database'

    print('\n====>>  ', success_text)
    return success_text, 200


def delete_course_reg_entry(mat_no, acad_session):
    course_reg = course_reg_utils.course_reg_for_session(mat_no, acad_session)
    if not course_reg:
        return 'Course Registration for session {}/{} does not exist'.format(acad_session, acad_session+1), 404

    session = utils.load_session(utils.get_DB(mat_no))
    courses_reg_schema = getattr(session, course_reg['table'] + 'Schema')
    # TODO reset optional course in personal info if set here

    courses_reg = courses_reg_schema.Meta.model.query.filter_by(mat_no=mat_no).first()
    db_session = courses_reg_schema.Meta.sqla_session
    db_session.delete(courses_reg)
    db_session.commit()
    db_session.close()

    return 'Record Deleted Successfully', 200
