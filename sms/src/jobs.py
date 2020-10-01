from flask import abort
from rq import get_current_job

from sms.config import db
from sms.models.user import Task
from sms.src.users import get_current_user

# Schedule ids
SENATE_VERSION = 1


def get(job_id):
    current_user = get_current_user()
    task = Task.query.filter_by(id=job_id).first()
    if task and current_user:
        if task.username != current_user.username:
            abort(401)
        job = task.get_rq_job()
        job.refresh()
        task.status = job.get_status()
        db.session.add(task)
        db.session.commit()
        params = {
            'progress': round(job.meta.get('progress', 0), 2),
            'description': job.meta.get('description', ''),
            'status': task.status
        }
        return params, 200
    else:
        return None, 404


def post(data):
    schedule_id = data['schedule_id']
    if schedule_id == SENATE_VERSION:
        from sms.src.sheets import senate_version_schedule
        args = data['args'][0]
        acad_session = args.get('acad_session')
        level = args.get('level')
        return senate_version_schedule(acad_session, level), 200


def get_result(job_id):
    current_user = get_current_user()
    task = Task.query.filter_by(id=job_id).first()
    if task and current_user:
        if task.username != current_user.username:
            return None, 401
        if task.status != 'finished':
            return None, 404
        job = task.get_rq_job()
        return job.result
    else:
        return None, 404


def get_current_job_by_name(name):
    job = get_current_job()
    if job:
        job_name = Task.get_name(job.get_id())
        if job_name == name:
            return job
    return None


def update_status(job):
    task = Task.query.filter_by(id=job.get_id()).first()
    task.status = job.get_status()
    db.session.add(task)


def set_progress(name, progress=None, description=None):
    job = get_current_job_by_name(name)
    if job:
        job.meta['progress'] = progress if progress else job.meta.get('progress', 0)
        job.meta['description'] = description if description else job.meta.get('description', '')
        job.save_meta()
        update_status(job)


def set_increment(name, increment=0, increment_basis=0, duration=0):
    job = get_current_job_by_name(name)
    if job:
        if not increment and duration:
            increment = job.meta.get('increment_basis', 0) / duration
        job.meta['increment'] = increment
        job.meta['increment_basis'] = increment_basis
        job.save_meta()


def update_progress(name, description=None):
    job = get_current_job_by_name(name)
    if job:
        job.meta['progress'] += job.meta['increment']
        job.meta['description'] = description if description else job.meta.get('description', '')
        job.save_meta()
        update_status(job)
