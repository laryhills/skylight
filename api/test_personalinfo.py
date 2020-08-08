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

config.add_token("TESTING_token", "personalinfo_test", perms)
#info_keys = ("username", "password", "permissions", "title", "fullname", "email")
#info_values = ("info_test", tokenize("somepwdhash"), "{}", "Testing", "Info Test", "accounts@te.st")
#info_base = dict(zip(info_keys, info_values))


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
    prop_1 = ('grad_stats', 'lga', 'mat_no', 'session_grad', 'session_admitted', 'level')
    prop_2 = ('GRAD_STATUS', 'LGA_OF_ORIGIN', 'MATNO', 'SESSION_GRADUATED', 'SESSION_ADMIT', 'CURRENT_LEVEL')
    for prop_data, prop_row in zip(prop_1, prop_2):
        assert student_data[prop_data] == info_row[prop_row]
        student_data.pop(prop_data)
    for prop in student_data:
        assert student_data[prop] == info_row[prop]

def test_get_valid_dets():
    config.add_token("TESTING_token", "personalinfo_test", perms)
    info_rows = cur.execute("SELECT * FROM PersonalInfo").fetchall()
    info_row = sample(info_rows, 1)[0]
    output, ret_code = personal_dets.get(info_row["matno"])
    assert ret_code == 200
    student_data = loads(output)
    prop_1 = ('grad_stats', 'lga', 'mat_no', 'session_grad', 'session_admitted', 'level')
    prop_2 = ('GRAD_STATUS', 'LGA_OF_ORIGIN', 'MATNO', 'SESSION_GRADUATED', 'SESSION_ADMIT', 'CURRENT_LEVEL')
    for prop_data, prop_row in zip(prop_1, prop_2):
        assert student_data[prop_data] == info_row[prop_row]
        student_data.pop(prop_data)
    for prop in student_data:
        assert student_data[prop] == info_row[prop]

