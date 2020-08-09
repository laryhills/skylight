import sqlite3
from sms import personal_info
from sms import personal_dets
from random import sample
from sms import config
from time import time
from sms.users import tokenize
from json import loads

conn = sqlite3.connect("sms/database/2015-2016.db")
conn.row_factory=sqlite3.Row
cur=conn.cursor()

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
    conn.commit()


def delete_student(mat_no):
    cur.execute("DELETE FROM PersonalInfo WHERE matno=?",(mat_no,))
    conn.commit()


def test_get_invaid_info():
    mat_no = "INV"+str(time())[-7:]
    assert personal_info.get(mat_no) == None

def test_get_invalid_dets():
    mat_no = "INV"+str(time())[-7:]
    assert personal_dets.get(mat_no) == (None, 404)

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
    output, ret_code = personal_dets.get(info_row["matno"])
    assert ret_code == 200
    student_data = loads(output)
    for prop_data, prop_row in zip(info_keys, row_keys):
        if prop_data:
            assert student_data[prop_data] == info_row[prop_row]


def test_post_new_info():
    config.add_token("TESTING_token", "personalinfo_test", perms)
