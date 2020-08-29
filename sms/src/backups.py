import os
from zipfile import ZipFile

from sms.src.ext.jobs import backup_databases
from sms.config import backups_dir, DB_DIR


def fetch_backup_list():
    backups = []
    with os.scandir(backups_dir) as dir_entries:
        for entry in dir_entries:
            info = entry.stat()
            backups.append((entry.name, info.st_size, info.st_mtime))
    backups = sorted(backups, key=lambda x: x(2), reverse=True)
    return backups


def restore_backup(backup_name):
    backup_path = os.path.join(backups_dir, backup_name)
    backup_databases(before_restore=True)
    # todo: close db engine connections here
    with ZipFile(backup_path) as zf:
        zf.extractall(DB_DIR)
