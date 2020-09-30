from sms.config import get_current_session
from sms.src import personal_info
from sms.src.script import get_students_for_course_adviser
from sms.src.users import access_decorator
from sms.src.utils import get_session_from_level, gpa_credits_poll


@access_decorator
def get(level):
    entry_session = get_session_from_level(get_current_session(), level, True)
    students = get_students_for_course_adviser(level, retDB=True)
    student_details = get_students_details(students, entry_session)
    return student_details, 200


def get_students_details(students, entry_session):
    students_details_dict = dict.fromkeys(students)
    for db_name in students:
        for mat_no in students[db_name]:
            bio = personal_info.get(mat_no)
            name = bio['othernames'] + ' ' + bio['surname']
            name += ' (Miss)' if bio['sex'] == 'F' else ''

            *gpa_credits, cgpa = gpa_credits_poll(mat_no)
            details = {
                'mat_no': mat_no,
                'name': name,
                'gpas': list(zip(*gpa_credits))[0],
                'cgpa': float(cgpa)
            }
            if students_details_dict.get(db_name):
                students_details_dict[db_name].append(details)
            else:
                students_details_dict[db_name] = [details]

    ordinary_students = []
    spillover_students = []
    for db_name in students_details_dict:
        details = students_details_dict[db_name]
        if int(db_name[:4]) >= entry_session and details:
            ordinary_students.extend(details)
        elif details:
            spillover_students.extend(details)
    ordinary_students_details = sorted(ordinary_students, key=lambda x: x['cgpa'], reverse=True)
    spillover_students_details = sorted(spillover_students, key=lambda x: x['cgpa'], reverse=True)

    students_details = ordinary_students_details + spillover_students_details

    return students_details
