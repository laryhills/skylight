import os.path
import secrets
from pathlib import Path
from json import loads
from flask import render_template
from weasyprint import HTML
from sms.config import app
from sms.utils import get_carryovers
from sms import personal_info
from sms import utils

base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(base_dir, 'templates', 'static', 'Uniben_logo.png')


def get(mat_no, session=None):
    pass


def post(reg_obj):
    pass
