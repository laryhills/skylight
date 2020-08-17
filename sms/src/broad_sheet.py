import os.path
import pdfkit
from datetime import date
from time import perf_counter
from secrets import token_hex
from colorama import init, Fore, Style
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_from_directory, url_for

from sms.src import course_details
from sms.src.results import get_results_for_acad_session, multisort
from sms.src.utils import get_current_session, get_registered_courses, get_level, multiprocessing_wrapper
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
    # todo: * handle spillovers (get passed 500l courses - asterisked - alongside the new ones),
    #           don't worry about length of the carryover column
    #       * handle the last (2) column(s) for 500l broadsheet
    #       * experiment with wkhtmltopdf's zoom and try to predict the zoom value to use with the
    #           len_first_sem_carryovers, <...>, len(first_sem_course), <...> and len(options[0] + options[1])

    start = perf_counter()
    registered_students_for_session = get_filtered_student_by_level(acad_session, level)
    print('student list fetched in', perf_counter() - start)

    index_to_display = 0 if raw_score else 1
    file_name = token_hex(8)

    # render the broadsheet footer
    with open(os.path.join(cache_base_dir, file_name + '_footer.html'), 'w') as footer:
        footer.write(render_template('broad_sheet_footer.html', current_date=date.today().strftime("%A, %B %-d, %Y")))

    # generate broadsheet
    context = (acad_session, index_to_display, file_name)
    multiprocessing_wrapper(generate_broadsheet_pdfs, registered_students_for_session.items(), context, True)
    collect_pdfs_in_zip(file_name)
    print('===>> total generation done in', perf_counter() - start)

    resp = send_from_directory(cache_base_dir, file_name + '.zip', as_attachment=True)
    return resp


def generate_broadsheet_pdfs(item, acad_session, index_to_display, file_name):
    level, mat_nos = item
    t1 = perf_counter()
    html, level = render_html(mat_nos, acad_session, level, index_to_display)
    generate_pdf(html, level, file_name)
    print(f'{str(level)}: pdf generated in', perf_counter() - t1)


def collect_pdfs_in_zip(file_name):
    zip_path = os.path.join(cache_base_dir, file_name + '.zip')
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zf:
        for level in range(100, 600, 100):
            try:
                pdf_name = file_name + '_' + str(level) + '.pdf'
                pdf = open(os.path.join(cache_base_dir, pdf_name), 'rb').read()
                zf.writestr(pdf_name, pdf)
            except Exception as e:
                pass


def render_html(mat_nos, acad_session, level, index_to_display):
    color_map = {'F': 'red', 'ABS': 'blue'}
    empty_value = ' '
    students, len_first_sem_carryovers, len_second_sem_carryovers = enrich_mat_no_list(mat_nos, acad_session, level)

    level_courses = course_details.get_all(level)[0]
    first_sem_courses = [(x['course_code'], x['course_credit'], x['options']) for x in level_courses if
                         x['course_semester'] == 1]
    second_sem_courses = [(x['course_code'], x['course_credit'], x['options']) for x in level_courses if
                          x['course_semester'] == 2]

    first_sem_options = [(x['course_code'], x['course_credit'], x['options']) for x in level_courses if
                         x['course_semester'] == 1 and x['options'] == 1]
    second_sem_options = [(x['course_code'], x['course_credit'], x['options']) for x in level_courses if
                          x['course_semester'] == 2 and x['options'] == 2]

    first_sem_courses = multisort(first_sem_courses)
    second_sem_courses = multisort(second_sem_courses)

    # just for now, later this condition should be "if option > 0 for course in level courses"
    if level == 500:
        options = [
            [('MEE531', 7, 1), ('MEE541', 7, 1), ('MEE561', 7, 1), ('MEE581', 7, 1), ('MEE591', 7, 1)],
            [('MEE532', 8, 2), ('MEE542', 8, 2), ('MEE562', 8, 2), ('MEE582', 8, 2), ('MEE592', 8, 2)]
        ]
    else:
        options = [[], []]

    len_first_sem_carryovers = max(len_first_sem_carryovers, 3)
    len_second_sem_carryovers = max(len_second_sem_carryovers, 3)

    html = render_template(
        'broad_sheet.html', enumerate=enumerate, sum=sum, int=int, url_for=url_for,
        len_first_sem_carryovers=len_first_sem_carryovers, len_second_sem_carryovers=len_second_sem_carryovers,
        first_sem_courses=first_sem_courses, second_sem_courses=second_sem_courses, options=options,
        first_sem_options=first_sem_options, second_sem_options=second_sem_options,
        index_to_display=index_to_display, empty_value=empty_value, color_map=color_map,
        students=students, session=acad_session, level=level,
    )
    return html, level


def generate_pdf(html, level, file_name):
    pdf_name = file_name + '_' + str(level) + '.pdf'
    options = {
        'page-size': 'A3',
        'orientation': 'landscape',
        # 'page-height': '420mm',  # <unitreal> like margin',
        # 'page-width': '297mm',  # <unitreal> like margin',
        # 'margin: 36.0pt, 21.6pt, 72.0pt, 21.6pt'
        'margin-top': '0.5in',
        'margin-right': '0.3in',
        'margin-bottom': '1.5in',
        'margin-left': '0.3in',

        'footer-html': os.path.join(cache_base_dir, file_name + '_footer.html'),
        # 'minimum-font-size': 12,
        # 'encoding': "UTF-8",
        # 'disable-smart-shrinking': None,
        'enable-local-file-access': None,
        'print-media-type': None,
        'no-outline': None,
        'dpi': 100,
        'log-level': 'warn',  # error, warn, info, none
    }
    pdfkit.from_string(html, os.path.join(cache_base_dir, pdf_name), options=options)


# ==============================================================================================
#                                  Utility functions
# ==============================================================================================

def get_filtered_student_by_level(acad_session, level=None):
    levels = [level] if level else list(range(100, 600, 100))
    students_by_level = {}
    for level in levels:
        associated_db = acad_session - level//100 + 1
        students = get_students_by_level(associated_db, level)
        # students = list(filter(lambda mat: get_level_at_acad_session(mat, acad_session) == level, students))
        students_by_level[level] = sorted(students)
    return students_by_level


def get_level_at_acad_session(mat_no, acad_session):
    if acad_session == current_session:
        return get_level(mat_no)
    c_reg = get_registered_courses(mat_no)
    for key in range(800, 0, -100):
        if c_reg[key]['course_reg_session'] and c_reg[key]['course_reg_session'] == acad_session:
            return c_reg[key]['course_reg_level']
    return ''


def enrich_mat_no_list(mat_nos, acad_session, level):
    students = {}
    max_len_first_sem_carryovers = 0
    max_len_second_sem_carryovers = 0

    for mat_no in mat_nos:

        course_reg = get_course_reg_at_acad_session(acad_session, mat_no=mat_no)
        if not course_reg:
            # print(mat_no, 'has no course_reg')
            continue

        result_details = get_results_for_acad_session(mat_no, acad_session)
        if result_details[1] != 200:
            print(Fore.RED + mat_no, 'has no results' + Style.RESET_ALL)
            continue
        elif result_details[0]['level_written'] > 500 and level == 500:
            # todo: fetch the passed 500 courses here and append ' *' to the grade and score
            #       also fix color_map to support ' *'
            pass
        elif result_details[0]['level_written'] != level:
            # print(mat_no, "result level", result_details[0]['level_written'], '!=', level)
            continue

        personal_info = process_personal_info(mat_no)
        result_details = result_details[0]
        result_details['tcr'] = course_reg['tcr']  # this line must come before the sum_semester_credits() call
        sem_tcp, sem_tcr, sem_tcf, failed_courses = sum_semester_credits(result_details, grade_index=1, credit_index=2)

        result_details['semester_tcp'] = sem_tcp
        result_details['semester_tcr'] = sem_tcr
        result_details['semester_tcf'] = sem_tcf
        result_details['failed_courses'] = failed_courses
        result_details['othernames'] = personal_info['othernames']
        result_details['surname'] = personal_info['surname']

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
