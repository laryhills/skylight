from flask import send_from_directory

from sms.config import CACHE_BASE_DIR
from sms.src.users import get_current_user
from sms.src.jobs import get_result


def senate_version_schedule(acad_session, level):
    user = get_current_user()
    name = 'senate_version.get' if level <= 400 else 'senate_version_500.get'
    job_id = user.queue_task(name, 'sms.src.senate_version.get', acad_session, level)
    return job_id


def senate_version_get(job_id):
    filename, status_code = get_result(job_id)
    if not filename:
        return None, status_code
    return send_from_directory(CACHE_BASE_DIR, filename, as_attachment=True), status_code
