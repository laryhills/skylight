import os
from secrets import token_hex
from zipfile import ZipFile, ZIP_DEFLATED

from flask import send_from_directory

from sms.src.ext.jobs import backup_databases
from sms.config import BACKUP_DIR, DB_DIR, CACHE_BASE_DIR
from sms.src.users import access_decorator


# @access_decorator
def get():
    return fetch_backup_list()


# @access_decorator
def download(backup_names=None, limit=15):
    return download_backups(backup_names, limit)


# @access_decorator
def backup():
    return backup_dbs()


# @access_decorator
def restore(backup_name, include_accounts=False):
    return restore_backup(backup_name, include_accounts)


# @access_decorator
def delete(backup_name):
    return delete_backup(backup_name)


# ================================================================
# ==========================  CORE  ==============================
# ================================================================
# todo: * remove old backups automatically (?) and manually [delete(): delete all before date "dt"]
#       *


def fetch_backup_list():
    backups = []
    with os.scandir(BACKUP_DIR) as dir_entries:
        for entry in dir_entries:
            info = entry.stat()
            backups.append({
                'file_name': entry.name,
                'file_size': info.st_size,
                'last_modified_time': info.st_mtime})
    backups = sorted(backups, key=lambda x: x['last_modified_time'], reverse=True)
    return backups, 200


def download_backups(backup_names=None, limit=15):
    if not backup_names:
        backup_names = sorted([backup.name for backup in os.scandir(BACKUP_DIR)], reverse=True)[:limit]
    file_name = token_hex(8) + '.zip'
    try:
        with ZipFile(os.path.join(CACHE_BASE_DIR, file_name), 'w', ZIP_DEFLATED) as zf:
            for backup_name in backup_names:
                zf.write(os.path.join(BACKUP_DIR, backup_name), arcname=backup_name)
        resp = send_from_directory(CACHE_BASE_DIR, file_name, as_attachment=True)
        return resp, 200

    except Exception as e:
        return None, 400


def backup_dbs():
    try:
        backup_name = backup_databases(external=True)
    except:
        return 'Something went wrong', 400
    return backup_name, 200


def restore_backup(backup_name, include_accounts=False):
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    try:
        backup_databases(before_restore=True)
        # todo: close db engine connections here
        with ZipFile(backup_path) as zf:
            databases = zf.namelist()
            for database in databases:
                if not include_accounts and database == 'accounts.db':
                    continue
                zf.extract(database, DB_DIR)
    except:
        return 'Something went wrong', 400
    return None, 200


def delete_backup(backup_names):
    for backup_name in backup_names:
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        if os.path.isfile(backup_path):
            try:
                os.unlink(backup_path)
            except OSError:
                pass
    return None, 200
