import os.path
import pdfkit
from time import perf_counter
from secrets import token_hex
from zipfile import ZipFile, ZIP_DEFLATED
from concurrent.futures import ProcessPoolExecutor
from flask import render_template, send_from_directory, url_for

from sms.src.utils import get_current_session, get_registered_courses, get_level
from sms.src.script import get_students_by_level
from sms.config import cache_base_dir

base_dir = os.path.dirname(__file__)
current_session = get_current_session()


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
                               url_for=url_for, students=registered_students_for_session[level],
                               )
        print(f'{str(level)}: html fetched in', perf_counter() - t1)
        htmls.append((html, level))

    file_name = token_hex(8)
    zip_path = os.path.join(cache_base_dir, file_name + '.zip')
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zf:
        generate_pdf_wrapper(generate_pdf, htmls, file_name, zf, concurrency=True)
    print('===>> total generation done in', perf_counter() - start)
    resp = send_from_directory(cache_base_dir, file_name + '.zip', as_attachment=True)
    return resp


def generate_pdf_wrapper(func, iterable, file_name, zf, concurrency=False):
    if not concurrency:
        [func(item, file_name, zf) for item in iterable]
    else:
        with ProcessPoolExecutor(max_workers=5) as executor:
            [executor.submit(func, item, file_name) for item in iterable]
        for level in range(100, 600, 100):
            try:
                pdf_name = file_name + '_' + str(level) + '.pdf'
                pdf = open(os.path.join(cache_base_dir, pdf_name), 'rb').read()
                zf.writestr(pdf_name, pdf)
            except Exception as e:
                pass


def generate_pdf(item, file_name, zf=None):
    html, level = item
    pdf_name = file_name + '_' + str(level) + '.pdf'
    options = {
        # 'page-size': 'A3',
        'page-height': '1370.0pt',  # <unitreal> like margin',
        'page-width': '936.0pt',  # <unitreal> like margin',
        # 'margin: 36.0pt, 21.6pt, 72.0pt, 21.6pt'
        'orientation': 'landscape',
        'disable-smart-shrinking': None,
        'enable-local-file-access': None,
        'print-media-type': None,
        # 'footer-html': '',
        # 'header-html': '',
        # 'margin-top': '0.6in',
        # 'margin-right': '0.5in',
        # 'margin-bottom': '0.6in',
        # 'margin-left': '0.5in',
        # 'minimum-font-size': 12,
        # 'encoding': "UTF-8",
        # 'no-outline': None,
        'dpi': 100,
        'log-level': 'warn',  # error, warn, info, none
    }
    t1 = perf_counter()
    pdf = pdfkit.from_string(html, False, options=options)
    print(f'{level} pdf generated in', perf_counter() - t1, '\n')
    if zf:
        zf.writestr(pdf_name, pdf)
    else:
        with open(os.path.join(cache_base_dir, pdf_name), 'wb') as pdf_file:
            pdf_file.write(pdf)


def get_filtered_student_by_level(acad_session, level=None):
    levels = [level] if level else list(range(100, 600, 100))
    students_by_level = {}
    for level in levels:
        associated_db = acad_session - level//100 + 1
        students = get_students_by_level(associated_db, level)
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
    return ''
