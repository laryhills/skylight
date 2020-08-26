import sqlite3
import os.path
from time import time
from sms import config
from json import loads
from random import sample
from sms.src import personal_info
from tests import db_path

conn = sqlite3.connect(os.path.join(db_path, "2015-2016.db"))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

conn_2 = sqlite3.connect(os.path.join(db_path, "master.db"))
conn_2.row_factory = sqlite3.Row
cur_2 = conn_2.cursor()

perms = {"read": True, "write": True, "superuser": True, "levels": [100, 200, 300, 600], "usernames": ["personalinfo_test"]}

info_keys = ['mat_no', 'surname', 'othernames', 'mode_of_entry', 'session_admitted', 'session_grad', 'level', None, 'sex', 'date_of_birth', 'state_of_origin', 'lga', 'phone_no', 'email_address', 'sponsor_phone_no', 'sponsor_email_address', 'grad_stats', None, None, None]
row_keys = ["MATNO", "SURNAME", "OTHERNAMES", "MODE_OF_ENTRY", "SESSION_ADMIT", "SESSION_GRADUATED", "CURRENT_LEVEL", "OPTION", "SEX", "DATE_OF_BIRTH", "STATE_OF_ORIGIN", "LGA_OF_ORIGIN", "PHONE_NO", "EMAIL_ADDRESS", "SPONSOR_PHONE_NO", "SPONSOR_EMAIL_ADDRESS", "GRAD_STATUS", "PROBATED_TRANSFERRED", "IS_SYMLINK", "DATABASE"]
row_values = ["ENGTESTING", "Banks", "Ian", 1, 2015, None, 100, None, "M", "8/12/12", "Edo", "Oredo", "08033104028", "email@gmail.com", "08033104028", "dad@dadmail.com", None, 0, 0, None]
info_base = dict(zip(info_keys, row_values))
info_base.pop(None)


def get_student(mat_no):
    return cur.execute("SELECT * FROM PersonalInfo WHERE matno=?",(mat_no,)).fetchone()


def insert_student(dummy_info):
    cur.execute("INSERT INTO PersonalInfo VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", dummy_info)
    cur_2.execute("INSERT INTO Main VALUES(?,?)", (dummy_info[0], "2015-2016.db"))
    conn.commit()
    conn_2.commit()


def delete_student(mat_no):
    cur.execute("DELETE FROM PersonalInfo WHERE matno=?", (mat_no,))
    cur_2.execute("DELETE FROM Main WHERE matno=?", (mat_no,))
    conn.commit()
    conn_2.commit()


def test_setup_env():
    delete_student("ENGTESTING")


def test_get_invaid_info():
    mat_no = "INV"+str(time())[-7:]
    assert personal_info.get(mat_no) == None


def test_get_invalid_dets():
    mat_no = "INV"+str(time())[-7:]
    assert personal_info.get_exp(mat_no) == (None, 404)


def test_get_valid_info():
    info_rows = cur.execute("SELECT * FROM PersonalInfo").fetchall()
    info_row = sample(info_rows, 1)[0]
    student_data = personal_info.get(info_row["matno"])
    for prop_data, prop_row in zip(info_keys, row_keys):
        if prop_data:
            assert student_data[prop_data] == info_row[prop_row]


def test_get_valid_dets():
    config.add_token("TESTING_token", "personalinfo_test", perms)
    info_rows = cur.execute("SELECT * FROM PersonalInfo").fetchall()
    info_row = sample(info_rows, 1)[0]
    output, ret_code = personal_info.get_exp(info_row["matno"])
    assert ret_code == 200
    student_data = loads(output)
    for prop_data, prop_row in zip(info_keys, row_keys):
        if prop_data:
            assert student_data[prop_data] == info_row[prop_row]


def test_post_dets_info():
    config.add_token("TESTING_token", "personalinfo_test", perms)
    dummy_info = info_base.copy()
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == (None, 200)
    info_row = get_student(dummy_info["mat_no"])
    for prop_data, prop_row, in zip(info_keys, row_keys):
        if prop_data:
            assert dummy_info[prop_data] == info_row[prop_row]
    delete_student(dummy_info["mat_no"])


def test_post_dets_update_errors():
    config.add_token("TESTING_token", "personalinfo_test", perms)
    insert_student(row_values)
    dummy_info = info_base.copy()
    # Inserting an extra field
    dummy_info["extra"] = "extra"
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    dummy_info.pop("extra")
    # Set a required field to empty/None/zero
    dummy_info["level"] = 0
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    delete_student(dummy_info["mat_no"])


def test_post_dets_new_errors():
    config.add_token("TESTING_token", "personalinfo_test", perms)
    dummy_info = info_base.copy()
    dummy_info["mat_no"] = "ENGTESTENG"
    # Inserting an extra field
    dummy_info["extra"] = "extra"
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied or missing a compulsory field", 400)
    dummy_info.pop("extra")
    # Set a required field to empty/None/zero
    dummy_info["mode_of_entry"] = 0
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied or missing a compulsory field", 400)
    # Remove a required field
    dummy_info.pop("mode_of_entry")
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied or missing a compulsory field", 400)


def test_teardown_env():
    test_setup_env()
