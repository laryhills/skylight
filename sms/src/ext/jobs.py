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
from sms.config import DB_DIR, backups_dir, cache_base_dir


def clear_cache_dir():
    for file in os.scandir(cache_base_dir):
        file_path = file.path
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def backup_databases():
    datetime_tag = datetime.now().isoformat().split('.')[0].replace('T', '__')
    zip_file = os.path.join(backups_dir, 'databases__' + datetime_tag + '.zip.skylight')
    with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zf:
        # remove sorted and use os.scandir instead of listdir if performance becomes an issue
        databases = sorted([file_name for file_name in os.listdir(DB_DIR) if file_name.endswith('.db')])
        for file_name in databases:
            zf.write(os.path.join(DB_DIR, file_name), arcname=file_name)


def my_listener(event):
    if event.code == EVENT_JOB_EXECUTED:
        log(user='system', func=eval(event.job_id), qual_name='jobs.{}'.format(event.job_id), args=[], kwargs={})
    elif event.exception or event.code == EVENT_JOB_ERROR:
        print('The job crashed :(')
    elif event.code == EVENT_JOB_MISSED:
        pass


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
    _scheduler.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)

    job_1 = _scheduler.add_job(backup_databases, id='backup_databases', trigger=backup_trigger)
    job_2 = _scheduler.add_job(clear_cache_dir, id='clear_cache_dir', trigger=cache_trigger)

    try:
        _scheduler.start()
    except SchedulerAlreadyRunningError:
        print('f')
        pass

    return _scheduler, [job_1, job_2]
