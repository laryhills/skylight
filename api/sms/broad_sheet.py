import os.path
from secrets import token_hex
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from weasyprint import HTML
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_from_directory

from sms.utils import get_current_session, get_registered_courses, get_level
from sms.script import get_students_by_level
from sms.config import cache_base_dir

base_dir = os.path.dirname(__file__)
current_session = get_current_session()
file_name = token_hex(8)


def get(acad_session, level=None):
    """
    This function gets the broadsheets for the academic session 'acad_session' for level 'level' if given
    else it gets for all levels during that session

    :param acad_session:
    :param level:
    :return:
    """
    start = perf_counter()
    registered_students_for_session = get_filtered_student_by_level(acad_session, level)
    print('student list fetched in', perf_counter() - start)
    htmls = []
    start = perf_counter()
    for level in sorted(registered_students_for_session.keys()):
        t1 = perf_counter()
        number_of_students = len(registered_students_for_session[level])
        html = render_template('broad_sheet.html', number_of_students=number_of_students, enumerate=enumerate,
                               students=registered_students_for_session[level])
        print(f'{str(level)}: html fetched in', perf_counter() - t1)
        htmls.append((html, level))

    lock = Lock()
    zip_path = os.path.join(cache_base_dir, file_name + '.zip')
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zf:
        threaded_call(generate_pdf, htmls, zf, lock)
    print('===>> total generation done in', perf_counter() - start)
    resp = send_from_directory(cache_base_dir, file_name + '.zip', as_attachment=True)
    return resp


def threaded_call(func, iterable, zf, lock):
    with ThreadPoolExecutor() as executor:
        [executor.submit(func, item, zf, lock) for item in iterable]


def generate_pdf(item, zf, lock):
    html, level = item
    pdf_name = file_name + '_' + str(level) + '.pdf'

    t1 = perf_counter()
    HTML(string=html).write_pdf(os.path.join(cache_base_dir, pdf_name))
    print(f'{level} pdf generated in', perf_counter() - t1)
    with lock:
        zf.write(pdf_name)


def get_filtered_student_by_level(acad_session, level=None):
    levels = [level] if level else list(range(100, 600, 100))
    students_by_level = {}
    for level in levels:
        associated_db = acad_session - level//100 + 1
        students = get_students_by_level(associated_db)
        # students = list(filter(lambda mat: get_level_at_acad_session(mat, acad_session) == level, students))
        students_by_level[level] = students
    return students_by_level


def get_level_at_acad_session(mat_no, acad_session):
    if acad_session == current_session:
        return get_level(mat_no)
    c_reg = get_registered_courses(mat_no)
    for key in range(800, 0, -100):
        if c_reg[key]['course_reg_session'] and c_reg[key]['course_reg_session'] == acad_session:
            return c_reg[key]['course_reg_level']
    return []

#
# if __name__ == '__main__':
#     html = cProfile.run(get(2018, 400))
#     print('yeah')

