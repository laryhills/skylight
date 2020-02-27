from sms import result_statement
from sms import utils, course_details, personal_info

'''
The result format is as below
         results = get('ENG1503886',0)['results']
     res300 = results[2]
>>> res300
{'first_sem': [(300, 'PRE311', 'Manufacturing Technology III', 2, 64, 'B'),
               (300, 'MEE311', 'Mechanics of Machines I', 3, 78, 'A'),
               (300, 'ELA301', 'Laboratory III', 2, 70, 'A'),
               (300, 'EMA381', 'Engineering Mathematics III', 3, 73, 'A'),
               (300, 'MEE321', 'Engineering Drawing III', 3, 83, 'A'),
               (300, 'MEE351', 'Thermodynamics I', 2, 81, 'A'),
               (300, 'MEE361', 'Fluid Mechanics I', 2, 72, 'A'),
               (300, 'CVE311', 'Theory of Structures & Strength of Materials II', 3, 80, 'A'),
               (300, 'EEE317', 'Electrical Engineering III', 3, 83, 'A')],

'second_sem': [(300, 'EMA382', 'Engineering Mathematics IV', 4, 68, 'B'),
               (300, 'MEE362', 'Fluid Mechanics II', 2, 92, 'A'),
               (300, 'MEE312', 'Mechanics of Machines II', 3, 80, 'A'),
               (300, 'MEE322', 'Creative Problem Solving', 3, 68, 'B'),
               (300, 'MEE332', 'Strength of Materials III', 2, 81, 'A'),
               (300, 'MEE372', 'Engineering Computers Graphics', 1, 50, 'C'),
               (300, 'EEE318', 'Electrical Engineering IV', 2, 64, 'B'),
               (300, 'MEE342', 'Materials Science & Production Processes', 2, 86, 'A'),
               (300, 'ELA302', 'Laboratory IV', 2, 58, 'C'),
               (300, 'MEE352', 'Engineering Thermodynamics II', 2, 61, 'B')]}
'''
# TODO: Also supply some personal details such as name, level, dept
# TODO: Supply grading scheme on selection of result input tab by course adviser
#       (choice is by level and current_session)
# TODO: Add a way to edit scores (overwrite scores with new data)


def post_results(list_of_results):
    """  ==== JSON FORMAT FOR THE RESULTS ====
       [['MEE551', '2019', 'ENG1503886', '98'],
        ['MEE561', '2019', 'ENG1503886', '98'],
        ['MEE571', '2019', 'ENG1503886', '98'],
        ['MEE521', '2019', 'ENG1503886', '98']]"""

    errors = []

    for index, result_details in enumerate(list_of_results):
        course_code, session_taken, mat_no, score = result_details
        session_taken, score = map(int, [session_taken, score])

        courses_registered, table_found_in = utils.get_courses_in_recent_course_reg(mat_no)
        if course_code not in courses_registered:
            errors.append('{0} at index {1} did not register {2} in the {3}/{4} session'.format(
                mat_no, index, course_code, session_taken, session_taken+1))
            break
        else:
            # find a way to post to the right results table
            pass


def get_result_for_edit(mat_no, level):
    # TODO level should be gotten from course_adviser's account

    courses_registered = utils.get_registered_courses(mat_no, level)
    courses_regd = courses_registered['courses']
    table_to_input_results = 'Result' + courses_registered['table'][-3:]
    results_already_present = False
    error_text = ''
    frame = {'courses': {'first_sem': [], 'second_sem': []}}
    personal_dets = personal_info.get(mat_no, 0)
    frame['personal_dets'] = {'mat_no': mat_no, 'current_level': personal_dets['current_level'],
                              'session_admitted': personal_dets['session_admitted'],
                              'surname': personal_dets['surname'], 'othernames': personal_dets['othernames']}

    if not courses_regd:
        error_text = 'No Course Registration Available yet for this Level'
        return

    try:
        # get any existing result
        # to enable inputting second semester results or edit of results by admin
        results_available = result_statement.get(mat_no, 0)['results'][(level//100)-1]
        if results_available:
            results_already_present = True
        table_to_input = 'Result' + str(results_available['first_sem'][0][0])
    except IndexError:
        # no result yet as should be
        results_available = {}
        table_to_input = 'Result' + str(result_statement.get(mat_no,0)['results'][-1]['first_sem'][0][0] + 100)
    frame['table_to_input'] = table_to_input
    frame['table_to_input_results'] = table_to_input_results

    done = []
    if results_already_present:
        for res in results_available['first_sem']:
            if res[1] in courses_regd:
                frame['courses']['first_sem'].append(res[1:])
                done.append(res[1])
        for res in results_available['second_sem']:
            if res[1] in courses_regd:
                frame['courses']['second_sem'].append(res[1:])
                done.append(res[1])
    done = set(done)
    courses = set(courses_regd)

    # todo: remove src
    src = []

    for course in courses.difference(done):
        course_dets = course_details.get(course, 0)
        if course_dets['course_semester'] == 1:
            frame['courses']['first_sem'].append((course_dets['course_code'], course_dets['course_title'],
                                                  course_dets['course_credit'], None, None))
        if course_dets['course_semester'] == 2:
            frame['courses']['second_sem'].append((course_dets['course_code'], course_dets['course_title'],

                                                  course_dets['course_credit'], None, None))
    # TEST
    # todo: remove test
    if table_to_input != table_to_input_results:
        src.append(mat_no + 'False' + '   table_to_input: ' + table_to_input + 'table_to_input_results: ' + table_to_input_results)
    return src #frame


def post_results_for_edit(mat_no, frame):
    pass
