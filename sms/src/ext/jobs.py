import shutil
import os
from datetime import datetime
from pytz import timezone as tz
from zipfile import ZipFile, ZIP_DEFLATED

from apscheduler.events import EVENT_JOB_MISSED, EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers import SchedulerAlreadyRunningError
from apscheduler.triggers.cron import CronTrigger
# from apscheduler.triggers.interval import IntervalTrigger

from sms.src.users import log
from sms.config import DB_DIR, BACKUP_DIR, CACHE_BASE_DIR


def start_scheduled_jobs():
    timezone = tz('Africa/Lagos')
    backup_trigger = CronTrigger(hour=17, minute=5, jitter=120)
    cache_trigger = CronTrigger(hour=17, minute=2, jitter=120)
    # test_trigger = IntervalTrigger(seconds=10, jitter=2)
    job_defaults = {
        'coalesce': True,
        'max_instances': 1,
        # 'misfire_grace_time': 3
    }

    _scheduler = BackgroundScheduler(timezone=timezone, job_defaults=job_defaults)
    _scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

    jobs = []
    jobs.append(_scheduler.add_job(backup_databases, id='backup_databases', trigger=backup_trigger))
    jobs.append(_scheduler.add_job(clear_cache_dir, id='clear_cache_dir', trigger=cache_trigger))

    try:
        _scheduler.start()
    except SchedulerAlreadyRunningError:
        print('f')
        pass

    return _scheduler, jobs


def job_listener(event):
    if event.code == EVENT_JOB_EXECUTED:
        pass
    elif event.exception or event.code == EVENT_JOB_ERROR:
        print('The job {} crashed :('.format(event.job_id))
    elif event.code == EVENT_JOB_MISSED:
        print('Missed job {}'.format(event.job_id))


# ==============================================================================
# ================================  JOBS  ======================================
# ==============================================================================

def backup_databases(before_restore=False, external=False):
    datetime_tag = datetime.now().isoformat().split('.')[0].replace('T', '__')
    flag = '__before_restore' if before_restore else ''
    backup_name = 'databases__' + datetime_tag + flag + '.zip.skylight'

    databases = sorted([file.name for file in os.scandir(DB_DIR) if file.name.endswith('.db')])
    zip_file = os.path.join(BACKUP_DIR, backup_name)
    with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zf:
        for file_name in databases:
            zf.write(os.path.join(DB_DIR, file_name), arcname=file_name)

    if not external:
        log(user='SYSTEM', func=backup_databases, qual_name='jobs.backup_databases', args=[],
            kwargs={'before_restore': before_restore, 'external': external})

    return backup_name


def clear_cache_base_dir():
    for file in os.scandir(CACHE_BASE_DIR):
        file_path = file.path
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    log(user='SYSTEM', func=clear_cache_base_dir, qual_name='jobs.clear_cache_base_dir', args=[], kwargs={})
