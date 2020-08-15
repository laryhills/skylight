import os.path
import pdfkit
from time import perf_counter
from secrets import token_hex
from colorama import init, Fore, Style
from zipfile import ZipFile, ZIP_DEFLATED
from concurrent.futures import ProcessPoolExecutor
from flask import render_template, send_from_directory, url_for

from sms.src import course_details
from sms.src.results import get_results_for_acad_session, multisort
from sms.src.utils import get_current_session, get_registered_courses, get_level
from sms.src.course_reg_utils import process_personal_info, get_course_reg_at_acad_session
from sms.src.script import get_students_by_level
from sms.config import cache_base_dir

base_dir = os.path.dirname(__file__)
current_session = get_current_session()
init()  # initialize colorama


def get(acad_session, level=None, raw_score=False):
    """
    This function gets the broadsheets for the academic session 'acad_session' for level 'level' if given
    else it gets for all levels during that session

    :param acad_session:
    :param level:
    :param raw_score:
    :return:
    """
    start = perf_counter()
    registered_students_for_session = get_filtered_student_by_level(acad_session, level)
    print('student list fetched in', perf_counter() - start)
    htmls = []
    start = perf_counter()
    # todo: refactor generate_pdf_wrapper, use ProcessPoolExecutor for the whole generation: html, pdf, et al
    for level in sorted(registered_students_for_session.keys()):
        t1 = perf_counter()
        mat_nos = registered_students_for_session[level]
        students, len_first_sem_carryovers, len_second_sem_carryovers = enrich_mat_no_list(mat_nos, acad_session)

        level_courses = course_details.get_all(level)[0]
        first_sem_courses = [(x['course_code'], x['course_credit'], x['options']) for x in level_courses if x['course_semester'] == 1]
        second_sem_courses = [(x['course_code'], x['course_credit'], x['options']) for x in level_courses if x['course_semester'] == 2]
        first_sem_courses = multisort(first_sem_courses)
        second_sem_courses = multisort(second_sem_courses)

        # just for now, later this condition should be "if option > 0 for course in level courses"
        if level == 500:
            options = [
                [('MEE531', 7, 1), ('MEE541', 7, 1), ('MEE561', 7, 1), ('MEE581', 7, 1)],
                [('MEE532', 8, 2), ('MEE542', 8, 2), ('MEE562', 8, 2), ('MEE582', 8, 2)]
            ]
        else:
            options = [[], []]

        len_first_sem_carryovers = max(len_first_sem_carryovers, 3)
        len_second_sem_carryovers = max(len_second_sem_carryovers, 3)

        # len_first_sem_regulars, len_second_sem_regulars
        empty_value = ' '
        min_score = 40
        index_to_display = 0 if raw_score else 1

        html = render_template(
            'broad_sheet.html', enumerate=enumerate,  sum=sum, int=int, url_for=url_for,
            len_first_sem_carryovers=len_first_sem_carryovers, len_second_sem_carryovers=len_second_sem_carryovers,
            first_sem_courses=first_sem_courses, second_sem_courses=second_sem_courses, options=options,
            index_to_display=index_to_display, empty_value=empty_value, min_score=min_score,
            students=students, session=acad_session, level=level,
        )
        print(f'{str(level)}: html prepared in', perf_counter() - t1)
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


# ==============================================================================================
#                                  Utility functions
# ==============================================================================================

def generate_pdf(item, file_name, zf=None):
    html, level = item
    pdf_name = file_name + '_' + str(level) + '.pdf'
    options = {
        'page-size': 'A3',
        'orientation': 'landscape',
        # 'page-height': '420mm',  # <unitreal> like margin',
        # 'page-width': '297mm',  # <unitreal> like margin',
        # 'margin: 36.0pt, 21.6pt, 72.0pt, 21.6pt'
        # 'margin-top': '0.6in',
        # 'margin-right': '0.5in',
        # 'margin-bottom': '0.6in',
        # 'margin-left': '0.5in',

        # 'footer-html': '',
        # 'header-html': '',
        # 'minimum-font-size': 12,
        # 'encoding': "UTF-8",
        # 'disable-smart-shrinking': None,
        'enable-local-file-access': None,
        'print-media-type': None,
        'no-outline': None,
        'dpi': 100,
        'log-level': 'warn',  # error, warn, info, none
    }
    t1 = perf_counter()
    pdf = pdfkit.from_string(html, False, options=options)
    print(f'{level} pdf generated in', perf_counter() - t1)
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


def enrich_mat_no_list(mat_nos, acad_session):
    students = {}
    max_len_first_sem_carryovers = 0
    max_len_second_sem_carryovers = 0

    first = True

    for mat_no in mat_nos:
        course_reg = get_course_reg_at_acad_session(acad_session, mat_no=mat_no)
        if not course_reg:
            # print(mat_no, 'has no course_reg')
            continue
        result_details = get_results_for_acad_session(mat_no, acad_session)
        if result_details[1] != 200:
            print(Fore.RED + mat_no, 'has no results')
            continue
        else:
            result_details = result_details[0]

        personal_info = process_personal_info(mat_no)
        result_details['tcr'] = course_reg['tcr']
        sem_tcp, sem_tcr, sem_tcf, failed_courses = sum_semester_credits(result_details, grade_index=1, credit_index=2)

        result_details['semester_tcp'] = sem_tcp
        result_details['semester_tcr'] = sem_tcr
        result_details['semester_tcf'] = sem_tcf
        result_details['failed_courses'] = failed_courses
        result_details['othernames'] = personal_info['othernames']
        result_details['surname'] = personal_info['surname']
        result_details['fullname'] = personal_info['othernames'] + ' ' + personal_info['surname']

        if len(result_details['carryovers']['first_sem']) > max_len_first_sem_carryovers:
            max_len_first_sem_carryovers = len(result_details['carryovers']['first_sem'])

        if len(result_details['carryovers']['second_sem']) > max_len_second_sem_carryovers:
            max_len_second_sem_carryovers = len(result_details['carryovers']['second_sem'])

        students[mat_no] = result_details
    return students, max_len_first_sem_carryovers, max_len_second_sem_carryovers


def sum_semester_credits(result_details, grade_index, credit_index):
    tcp = [0, 0]  # total credits passed
    tcr = [0, 0]  # total credits registered
    tcf = [0, 0]  # total credits failed
    failed_courses = []

    for index, sem in enumerate(['first_sem', 'second_sem']):
        courses = {**result_details['regular_courses'][sem], **result_details['carryovers'][sem]}
        for course in courses:
            if courses[course][grade_index] not in ['F', 'ABS']:
                tcp[index] += courses[course][credit_index]
            else:
                tcf[index] += courses[course][credit_index]
                failed_courses.append(course)
            tcr[index] += courses[course][credit_index]

    # if sum(tcp) != result_details['tcp'] or sum(tcr) != result_details['tcr']:
    #     print('{}AssertionError: {} ==> tcp: {:>2} != {:>2}; tcr: {:>2} != {:>2}'.format(Fore.RED, Style.RESET_ALL
    #           + result_details['mat_no'], sum(tcp), result_details['tcp'], sum(tcr), result_details['tcr']))

    return tcp, tcr, tcf, failed_courses
