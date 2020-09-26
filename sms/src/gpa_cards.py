from sms.src.script import get_students_for_course_adviser
from sms.config import get_current_session
from sms.src.users import load_session, access_decorator
from sms.src.utils import get_gpa_credits


def get_students_details(students, entry_session):
    students_details_dict = dict.fromkeys(students)
    for db_name in students:
        session = load_session(db_name)
        for mat_no in students[db_name]:
            bio_obj = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
            name = bio_obj.othernames + ' ' + bio_obj.surname
            name += ' (Miss)' if bio_obj.sex == 'F' else ''

            gpa_creds_obj = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
            gpas = get_gpa_credits(mat_no, session=session)[0]
            cgpa = float(gpa_creds_obj.cgpa)

            details = {
                    'mat_no': mat_no,
                    'name': name,
                    'gpas': gpas,
                    'cgpa': cgpa
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


@access_decorator
def get(level):
    entry_session = get_session_from_level(get_current_session(), level, True)
    students = get_students_for_course_adviser(level, retDB=True)
    student_details = get_students_details(students, entry_session)
    return student_details, 200
