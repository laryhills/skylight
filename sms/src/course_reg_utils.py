from sms.src import personal_info, course_details
from sms.src.utils import course_reg_poll, get_carryovers, get_dept, multisort, ltoi


def process_personal_info(mat_no):
    some_personal_info = personal_info.get(mat_no)
    some_personal_info["mode_of_entry_numeric"] = some_personal_info["mode_of_entry"]
    some_personal_info["mode_of_entry"] = ["PUTME", "DE(200)", "DE(300)"][some_personal_info["mode_of_entry"] - 1]
    some_personal_info['department'] = get_dept()
    for key in some_personal_info:
        if not some_personal_info[key]:
            some_personal_info[key] = ''
    if some_personal_info["sex"] == 'F':
        some_personal_info['surname'] += " (Miss)"
    return some_personal_info


def get_probation_status_and_prev_category(res_poll, acad_session):
    previous_categories = [x['category'] for x in res_poll if x and x['category'] and x['session'] < acad_session]
    previous_category = previous_categories[-1] if len(previous_categories) > 0 else ''
    probation_status = 1 if previous_category == 'C' else 0
    return probation_status, previous_category


def get_table_to_populate(current_level, acad_session, res_poll, course_reg):
    """- Get table corr. to results table for acad_session if it exists
       - else check for table corr to current level
       - otherwise search for the first available table
    """
    table_to_populate = ''
    index = [ind for ind, x in enumerate(res_poll) if x and x['session'] == acad_session]
    if index and not course_reg[index[0]]['courses']:
        table_to_populate = 'CourseReg' + str(100 * (index[0] + 1))
    elif not course_reg[ltoi(current_level)]['courses']:
        table_to_populate = 'CourseReg' + str(current_level)
    else:
        index = [ind for ind, x in enumerate(course_reg) if not x['courses']]
        if index: table_to_populate = 'CourseReg' + str(100 * (index[0] + 1))
    return table_to_populate


def course_reg_for_session(mat_no, session, reg_poll=None):
    if not reg_poll: reg_poll = course_reg_poll(mat_no)
    ret_val = [[ind, c_reg] for ind, c_reg in enumerate(reg_poll) if c_reg['courses'] and c_reg['session'] == session]
    if not ret_val:
        return {}
    index, c_reg = ret_val[0]
    c_reg['table'] = 'CourseReg{}'.format(100 * (index + 1))
    while '0' in c_reg['courses']: c_reg['courses'].remove('0')
    return c_reg


def fetch_carryovers(mat_no, current_level):
    """
    utils.get_carryovers() wrapper for handling the uniqueness of UBT400

    :param mat_no:
    :param current_level:
    :return: first_sem_carryover_courses, second_sem_carryover_courses
    """
    carryover_courses = get_carryovers(mat_no, current_level)
    if carryover_courses['first_sem']:
        first_sem_carryover_courses = list(list(zip(*carryover_courses['first_sem']))[0])
    else:
        first_sem_carryover_courses = []
    if current_level == 400:
        # Force only reg of UBITS for incoming 400L
        second_sem_carryover_courses = []
    else:
        if carryover_courses['second_sem']:
            second_sem_carryover_courses = list(list(zip(*carryover_courses['second_sem']))[0])
        else:
            second_sem_carryover_courses = []
        if current_level == 500 and "UBT400" in second_sem_carryover_courses:
            second_sem_carryover_courses.remove("UBT400")
    return first_sem_carryover_courses, second_sem_carryover_courses


def enrich_course_list(course_list, fields=('code', 'title', 'credit', 'level')):
    """
    Add details to courses supplied in course_list

    :param course_list: <list: str>: ['course_code_1', 'course_code_2', ...]
                     or <list: list>: [['course_code_1', '', ...], ['course_code_2', '', ...]]
    :param fields: <list> (optional): the course details fields to include in the order required
    :return: the enriched list
    """
    enriched_course_list = []
    for crse in course_list:
        if isinstance(crse, list):
            crse_dets = course_details.get(crse[0])
            [crse.append(crse_dets[field]) for field in fields if field != 'code']
        elif isinstance(crse, str):
            crse_dets = course_details.get(crse)
            crse = [crse_dets[field] for field in fields]
        enriched_course_list.append(crse)
    return enriched_course_list


def sum_credits(course_objects, credits_index=None):
    """
    :param course_objects: [('course_code_1', <some_other_detail>, <>,..),
                            ('course_code_2', <some_other_detail>, <>,..), ...]
    :param credits_index: <int>: (optional) index of course object that contains the course_credits
    :return: <int: the sum of credits>
    """
    tot = 0
    for course_object in course_objects:
        if credits_index:
            tot += int(course_object[credits_index])
        else:
            tot += int(course_details.get(course_object[0])['credit'])
    return tot


def sum_credits_many(*args, credits_index=None):
    """
    wrapper for sum_credits; gives the sum for more than one list of courses

    :param args: list of list of courses
    :param credits_index: <int>: (optional) index of course object that contains the course_credits
    """
    tot_many = 0
    for arg in args:
        tot_many += sum_credits(arg, credits_index)
    return tot_many


def get_optional_courses(level=None):
    if level and level > 500:
        level = 500
    level_courses = course_details.get_all(level=level, options=True)
    first_sem_options = multisort([(x['code'], x['credit'], x['options']) for x in level_courses if
                                   x['semester'] == 1 and x['options'] == 1])
    second_sem_options = multisort([(x['code'], x['credit'], x['options']) for x in level_courses if
                                    x['semester'] == 2 and x['options'] == 2])
    return first_sem_options, second_sem_options
