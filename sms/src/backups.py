import os
from datetime import datetime
from secrets import token_hex
from flask import send_from_directory
from zipfile import ZipFile, ZIP_DEFLATED

from sms.config import BACKUP_DIR, DB_DIR, CACHE_BASE_DIR
from sms.src.users import access_decorator, log


@access_decorator
def get():
    return fetch_backup_list()


@access_decorator
def download(backup_names=None, limit=15):
    return download_backups(backup_names, limit)


@access_decorator
def backup(tag=''):
    try:
        backup_name = backup_databases(tag=tag, external=True)
    except:
        return 'Something went wrong', 400
    return backup_name, 200


@access_decorator
def restore(backup_name, include_accounts=False):
    return restore_backup(backup_name, include_accounts)


@access_decorator
def delete(backup_name):
    return delete_backup(backup_name)


# ================================================================
# ==========================  CORE  ==============================
# ================================================================

def fetch_backup_list():
    backups = []
    for entry in os.scandir(BACKUP_DIR):
        if entry.name.endswith('.skylight.zip'):
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
    file_name = 'backups_' + token_hex(8) + '.zip'
    try:
        with ZipFile(os.path.join(CACHE_BASE_DIR, file_name), 'w', ZIP_DEFLATED) as zf:
            for backup_name in backup_names:
                zf.write(os.path.join(BACKUP_DIR, backup_name), arcname=backup_name)
        resp = send_from_directory(CACHE_BASE_DIR, file_name, as_attachment=True)
        return resp, 200

    except Exception as e:
        return None, 400


def backup_databases(tag='', before_restore=False, external=False):
    """

    :param tag: string supplied for easy identification
    :param before_restore:
    :param external: true if called externally
    :return:
    """
    datetime_tag = datetime.now().isoformat().split('.')[0].replace('T', '__').replace(':', '_')
    custom_tag = '__' + ('before_restore' if before_restore else tag)
    backup_name = 'databases__' + datetime_tag + custom_tag + '.skylight.zip'

    databases = sorted([file.name for file in os.scandir(DB_DIR) if file.name.endswith('.db')])
    zip_file = os.path.join(BACKUP_DIR, backup_name)
    with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zf:
        for file_name in databases:
            zf.write(os.path.join(DB_DIR, file_name), arcname=file_name)

    if not external:
        log(user='SYSTEM', func=backup_databases, qual_name='backups.backup_databases', args=[],
            kwargs={'before_restore': before_restore, 'external': external})

    return backup_name


def restore_backup(backup_name, include_accounts=False):
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    try:
        backup_databases(before_restore=True)
        with ZipFile(backup_path) as zf:
            databases = zf.namelist()
            for database in databases:
                if not include_accounts and database == 'accounts.db':
                    continue
                zf.extract(database, DB_DIR)
    except FileNotFoundError:
        return 'File "{}" not found on server'.format(backup_name), 404
    except Exception as e:
        return 'Something went wrong', 400
    return None, 200


def delete_backup(backup_name):
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if os.path.isfile(backup_path):
        try:
            os.unlink(backup_path)
        except OSError:
            pass
    else:
        return 'File "{}" not found on server'.format(backup_name), 404
    return None, 200
