import os
import time
import pdfkit
import imgkit
import secrets
import threading
import concurrent.futures
from string import capwords
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_from_directory

from sms.src import result_statement
from sms.config import app as current_app, CACHE_BASE_DIR, UNIBEN_LOGO_PATH
from sms.src.users import access_decorator
from sms.src.ext.html_parser import split_html
from sms.src.utils import get_level_weightings, get_carryovers, gpa_credits_poll, ltoi, multisort


@access_decorator
def get(mat_no, raw_score=False, to_print=False):
    result_stmt = result_statement.get(mat_no)

    name = result_stmt["surname"] + " " + result_stmt["othernames"]
    dept = capwords(result_stmt["dept"])
    dob = result_stmt["date_of_birth"]
    mod = ['PUTME', 'DE(200)', 'DE(300)'][result_stmt['mode_of_entry'] - 1]
    entry_session = result_stmt['session_admitted']
    grad_session = result_stmt['session_grad']
    results = res_sort(result_stmt['results'])
    no_of_pages = len(results) + 1
    credits = [list(map(sum, creds)) for creds in result_stmt['credits']]
    gpas, level_credits = list(zip(*gpa_credits_poll(mat_no)[:-1]))
    gpas, level_credits = [list(map(lambda x: x if x else 0, item)) for item in (gpas, level_credits)]
    level_weightings = get_level_weightings(result_stmt['mode_of_entry'])
    weighted_gpas = list(map(lambda x, y: round(x * y, 4), gpas, level_weightings))

    owed_courses = get_carryovers(mat_no)
    owed_courses = owed_courses['first_sem'] + owed_courses['second_sem']
    gpa_check = [''] * 5
    for course in owed_courses:
        index = ltoi(course[2])
        gpa_check[index] = '*'

    with current_app.app_context():
        html = render_template('result_update_template.htm', uniben_logo_path=UNIBEN_LOGO_PATH, any=any,
                               no_of_pages=no_of_pages, mat_no=mat_no, name=name, dept=dept, dob=dob,
                               mode_of_entry=mod, entry_session=entry_session, grad_session=grad_session,
                               results=results, credits=credits, gpas=gpas, level_weightings=level_weightings,
                               weighted_gpas=weighted_gpas, enumerate=enumerate, raw_score=raw_score,
                               level_credits=level_credits, gpa_check=gpa_check)

    def generate_img(args):
        i, page = args
        img = imgkit.from_string(page, None, options=options)
        arcname = file_name + '_{}.png'.format(i)
        with lock:
            zf.writestr(arcname, data=img)

    def generate_archive():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(generate_img, enumerate(htmls))

    if to_print:
        options = {
            'page-size': 'A4',
            'disable-smart-shrinking': None,
            'print-media-type': None,
            'margin-top': '0.6in',
            'margin-right': '0.5in',
            'margin-bottom': '0.6in',
            'margin-left': '0.5in',
            # 'minimum-font-size': 12,
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'no-outline': None,
            'log-level': 'warn',
            'dpi': 100,
        }
        file_name = secrets.token_hex(8) + '.pdf'
        start_time = time.time()
        pdfkit.from_string(html, os.path.join(CACHE_BASE_DIR, file_name), options=options)
        print(f'pdf generated in {time.time() - start_time} seconds')
        resp = send_from_directory(CACHE_BASE_DIR, file_name, as_attachment=True)
    else:
        options = {
            'format': 'png',
            'enable-local-file-access': None,
            'log-level': 'warn',
            'quality': 50,
        }
        file_name = secrets.token_hex(8)
        file_path = os.path.join(CACHE_BASE_DIR, file_name + '.zip')
        start_time = time.time()
        htmls = split_html(html)
        lock = threading.Lock()
        with ZipFile(file_path, 'w', ZIP_DEFLATED) as zf:
            generate_archive()
        print(f'{len(htmls)} images generated and archived in {time.time() - start_time} seconds')
        resp = send_from_directory(CACHE_BASE_DIR, file_name + '.zip', as_attachment=True)

    return resp, 200


def res_sort(results):
    for idx in range(len(results)):
        semesters = ['first_sem', 'second_sem'] if 'second_sem' in results[idx] else ['first_sem']
        for sem in semesters:
            fail_indices = sorted([ind for ind, crs in enumerate(results[idx][sem]) if crs[4] in ['F', 'ABS']], reverse=True)
            fails = [results[idx][sem].pop(ind) for ind in fail_indices]
            results[idx][sem] = multisort(results[idx][sem]) + multisort(fails)
    return results


# def remove_empty(results):
#     """
#     This function is to remove result records which contain only "unusual results", that is, no course registration
#     """
#     for index, result in enumerate(results):
#         if not (result['first_sem'] or result['second_sem']):
#             results[index] = []
#     while [] in results:
#         results.remove([])
#     return results
