from sms import personal_info
from sms import course_details
from sms.utils import get_carryovers, get_depat


def process_personal_info(mat_no):
    some_personal_info = personal_info.get(mat_no, 0)
    some_personal_info["mode_of_entry_numeric"] = some_personal_info["mode_of_entry"]
    some_personal_info["mode_of_entry"] = ["PUTME", "DE(200)", "DE(300)"][some_personal_info["mode_of_entry"] - 1]
    some_personal_info['department'] = get_depat('long')
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
    table_to_populate = ''
    # use table corresponding to results table for the session if it exists
    index = [ind for ind, x in enumerate(res_poll) if x and x['session'] == acad_session]
    if index and not course_reg[100 * (index[0] + 1)]['courses']:
        # check if table corresponding to level is free
        table_to_populate = 'CourseReg' + str(100 * (index[0] + 1))
    elif not course_reg[current_level]['courses']:
        table_to_populate = course_reg[current_level]['table']
    else:
        # otherwise search for the first available table
        for key in range(100, 900, 100):
            if not course_reg[key]['courses']:
                table_to_populate = course_reg[key]['table']
                break
    return table_to_populate


def get_course_reg_at_acad_session(acad_session, course_reg):
    # get last course_reg
    last_course_reg = {}
    for reg in course_reg:
        if course_reg[reg]['courses'] and course_reg[reg]['course_reg_session'] == acad_session:
            last_course_reg = course_reg[reg]
            break
    return last_course_reg


def fetch_carryovers(mat_no, current_level):
    """
    utils.get_carryovers() wrapper for handling the uniqueness of UBT400

    :param mat_no:
    :param current_level:
    :return: first_sem_carryover_courses, second_sem_carryover_courses
    """
    carryover_courses = get_carryovers(mat_no, retJSON=False)
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


def enrich_course_list(course_list, fields=('course_code', 'course_title', 'course_credit')):
    """
    Add details to courses supplied in course_list

    :param course_list: <list>: ['course_code_1', 'course_code_2', ...]
    :param fields: <list> (optional): the course details fields to include in the order required
    :return: the enriched list
    """
    enriched_course_list = []
    for crse in course_list:
        crse_dets = course_details.get(crse, 0)
        course = [crse_dets[field] for field in fields]
        enriched_course_list.append(course)
    return enriched_course_list


def sum_credits(course_objects, index_for_credits=None):
    """
    :param course_objects: [('course_code_1', <some_other_detail>, <>,..),
                            ('course_code_2', <some_other_detail>, <>,..), ...]
    :param index_for_credits: <int>: (optional) index of course object that contains the course_credits
    :return: <int: the sum of credits>
    """
    tot = 0
    for course_object in course_objects:
        if index_for_credits:
            tot += int(course_object[index_for_credits])
        else:
            tot += int(course_details.get(course_object[0], 0)['course_credit'])
    return tot


def sum_credits_many(*args, index_for_credits=None):
    """
    wrapper for sum_credits; gives the sum for more than one list of courses

    :param args: list of list of courses
    :param index_for_credits: <int>: (optional) index of course object that contains the course_credits
    :return: <int>: the sum of credits
    """
    tot_many = 0
    for arg in args:
        tot_many += sum_credits(arg, index_for_credits)
    return tot_many


def multisort(iters):
    iters = sorted(iters, key=lambda x: x[0])
    return sorted(iters, key=lambda x: x[0][3])

