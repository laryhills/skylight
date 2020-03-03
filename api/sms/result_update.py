import os
import secrets
from string import capwords
from flask import render_template, send_from_directory
from weasyprint import HTML
from sms import result_statement
from sms.config import app, cache_base_dir

base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(base_dir, 'templates', 'static', 'Uniben_logo.png')


def get(mat_no, to_print=False):
    result_stmt = result_statement.get(mat_no, 0)

    no_of_pages = len(result_stmt['results']) + 1
    name = result_stmt['name'].replace(',', '')
    depat = capwords(result_stmt['depat'])
    dob = result_stmt['dob']
    mod = result_stmt['mode_of_entry']
    entry_session = result_stmt['entry_session']
    grad_session = result_stmt['grad_session']
    results = result_stmt['results']
    credits = result_stmt['credits']

    with app.app_context():
        html = render_template('student_update_template_files.htm', no_of_pages=no_of_pages, mat_no=mat_no, name=name,
                               depat=depat, dob=dob, mode_of_entry=mod, entry_session=entry_session,
                               grad_session=grad_session, results=results, credits=credits)

    if to_print:
        file_name = secrets.token_hex(8) + '.pdf'
        HTML(string=html).write_pdf(os.path.join(cache_base_dir, file_name))
        resp = send_from_directory(cache_base_dir, file_name, as_attachment=True)
    else:
        file_name = secrets.token_hex(8) + '.png'
        HTML(string=html).write_png(os.path.join(cache_base_dir, file_name))
        resp = send_from_directory(cache_base_dir, file_name, as_attachment=True)

    return resp
