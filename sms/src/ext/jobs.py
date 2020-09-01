import os
import shutil
from pytz import timezone as tz

from apscheduler.events import EVENT_JOB_MISSED, EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers import SchedulerAlreadyRunningError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backups import backup_databases
from sms.src.users import log
from sms.config import CACHE_BASE_DIR


def start_scheduled_jobs():
    timezone = tz('Africa/Lagos')
    backup_trigger = CronTrigger(hour=17, minute=5, jitter=120)
    cache_trigger = CronTrigger(hour=17, minute=2, jitter=120)
    test_trigger = IntervalTrigger(seconds=10, jitter=2)
    job_defaults = {
        'coalesce': True,
        'max_instances': 1,
        # 'misfire_grace_time': 3
    }
    _scheduler = BackgroundScheduler(timezone=timezone, job_defaults=job_defaults)
    _scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

    jobs = [
        _scheduler.add_job(backup_databases, id='backup_databases', trigger=backup_trigger),
        _scheduler.add_job(clear_cache_base_dir, id='clear_cache_base_dir', trigger=cache_trigger)
    ]
    try:
        _scheduler.start()
    except SchedulerAlreadyRunningError:
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
