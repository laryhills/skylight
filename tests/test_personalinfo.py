import sqlite3
import os.path
from time import time
from sms import config
from json import loads
from random import sample
from sms.src import personal_info
from tests import db_path

sessional_db = "2015-2016.db"

conn = sqlite3.connect(os.path.join(db_path, sessional_db))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

conn_2 = sqlite3.connect(os.path.join(db_path, "master.db"))
conn_2.row_factory = sqlite3.Row
cur_2 = conn_2.cursor()

perms = {"read": True, "write": True, "superuser": True, "levels": [100, 200, 300, 600], "usernames": ["personalinfo_test"]}

info_keys = ['mat_no', 'surname', 'othernames', 'mode_of_entry', 'session_admitted', 'session_grad', 'level', None, 'sex', 'date_of_birth', 'state_of_origin', 'lga', 'phone_no', 'email_address', 'sponsor_phone_no', 'sponsor_email_address', None, None, None]
row_keys = ["MATNO", "SURNAME", "OTHERNAMES", "MODE_OF_ENTRY", "SESSION_ADMIT", "SESSION_GRADUATED", "CURRENT_LEVEL", "OPTION", "SEX", "DATE_OF_BIRTH", "STATE_OF_ORIGIN", "LGA_OF_ORIGIN", "PHONE_NO", "EMAIL_ADDRESS", "SPONSOR_PHONE_NO", "SPONSOR_EMAIL_ADDRESS", "PROBATED_TRANSFERRED", "IS_SYMLINK", "DATABASE"]
row_values = ["ENGTESTING", "Banks", "Ian", 1, 2015, None, 100, None, "M", "8/12/12", "Edo", "Oredo", "08033104028", "email@gmail.com", "08033104028", "dad@dadmail.com", 0, 0, None]
row_values_2 = ["ENGTESTING", "Holmes", "Sherlock", 2, 2016, 2020, 200, None, "F", "10/10/10", "Delta", "Agbor", "08012345678", "fmail@fmail.com", "08087654321", "pop@popmail.com", 0, 0, None]
info_base = dict(zip(info_keys, row_values))
info_base.pop(None)


def get_student(mat_no):
    return cur.execute("SELECT * FROM PersonalInfo WHERE matno=?",(mat_no,)).fetchone()


def insert_student(dummy_info):
    cur.execute("INSERT INTO PersonalInfo VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", dummy_info)
    cur_2.execute("INSERT INTO Main VALUES(?,?)", (dummy_info[0], sessional_db))
    conn.commit()
    conn_2.commit()


def delete_student(mat_no):
    cur.execute("DELETE FROM PersonalInfo WHERE matno=?", (mat_no,))
    cur_2.execute("DELETE FROM Main WHERE matno=?", (mat_no,))
    conn.commit()
    conn_2.commit()


def test_setup_env():
    config.add_token("TESTING_token", "personalinfo_test", perms)
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
    student_data["level"] *= [1,-1][student_data["grad_status"]]
    for prop_data, prop_row in zip(info_keys, row_keys):
        if prop_data:
            assert student_data[prop_data] == info_row[prop_row]


def test_get_valid_dets():
    info_rows = cur.execute("SELECT * FROM PersonalInfo").fetchall()
    info_row = sample(info_rows, 1)[0]
    output, ret_code = personal_info.get_exp(info_row["matno"])
    assert ret_code == 200
    student_data = loads(output)
    student_data["level"] *= [1,-1][student_data["grad_status"]]
    for prop_data, prop_row in zip(info_keys, row_keys):
        if prop_data:
            assert student_data[prop_data] == info_row[prop_row]


def test_post_dets_info():
    dummy_info = info_base.copy()
    dummy_info["grad_status"] = int(0 > dummy_info["level"])
    output, ret_code = personal_info.post_exp(dummy_info)
    assert (output, ret_code) == (None, 200)
    info_row = get_student(dummy_info["mat_no"])
    for prop_data, prop_row, in zip(info_keys, row_keys):
        if prop_data:
            assert dummy_info[prop_data] == info_row[prop_row]
    delete_student(dummy_info["mat_no"])

    # Flip the grad_status and retry
    dummy_info = info_base.copy()
    dummy_info["grad_status"] = int(dummy_info["level"] > 0)
    output, ret_code = personal_info.post_exp(dummy_info)
    row_values[6] *= -1
    assert (output, ret_code) == (None, 200)
    info_row = get_student(dummy_info["mat_no"])
    for prop_data, prop_row, in zip(info_keys, row_keys):
        if prop_data:
            assert dummy_info[prop_data] == info_row[prop_row]
    delete_student(dummy_info["mat_no"])
    row_values[6] *= -1


def test_put_dets():
    insert_student(row_values)
    new_info = dict(zip(info_keys, row_values_2))
    new_info.pop(None)
    new_info["grad_status"] = int(0 > new_info["level"])
    output, ret_code = personal_info.put(new_info)
    assert (output, ret_code) == (None, 200)
    new_info["level"] = abs(new_info["level"]) * [1, -1][new_info["grad_status"]]
    info_row = get_student(new_info["mat_no"])
    for prop_data, prop_row, in zip(info_keys, row_keys):
        if prop_data:
            assert new_info[prop_data] == info_row[prop_row]

    # Flip grad status alone
    new_info_2 = {"mat_no": new_info["mat_no"], "grad_status": int(not new_info["grad_status"])}
    output, ret_code = personal_info.put(new_info_2)
    assert (output, ret_code) == (None, 200)
    info_row = get_student(new_info_2["mat_no"])
    assert info_row["current_level"] == -new_info["level"]

    # Insert level alone and inherit grad_status
    new_info_3 = {"mat_no": new_info["mat_no"], "level": 500}
    output, ret_code = personal_info.put(new_info_3)
    assert (output, ret_code) == (None, 200)
    info_row = get_student(new_info_3["mat_no"])
    assert (info_row["current_level"] > 0) == (-new_info["level"] > 0)

    delete_student(new_info["mat_no"])


def test_patch_dets():
    insert_student(row_values)
    new_info = dict(zip(info_keys, row_values_2))
    new_info.pop(None)
    output, ret_code = personal_info.patch(new_info)
    assert (output, ret_code) == (None, 200)
    info_row = get_student(new_info["mat_no"])
    for prop_data, prop_row, in zip(info_keys, row_keys):
        if prop_data:
            if prop_data in ("session_admitted", "session_grad", "level", "mode_of_entry"):
                assert info_base[prop_data] == info_row[prop_row]
            else:
                assert new_info[prop_data] == info_row[prop_row]
    delete_student(new_info["mat_no"])


def test_post_dets_new_errors():
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


def test_put_dets_errors():
    # Modify invalid mat_no
    output, ret_code = personal_info.put({"mat_no":"INVALIDMAT"})
    assert (output, ret_code) == (None, 404)
    # Put initialization
    insert_student(row_values)
    dummy_info = info_base.copy()
    # Inserting an extra field
    dummy_info["extra"] = "extra"
    output, ret_code = personal_info.put(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    dummy_info.pop("extra")
    # Set a required field to empty/None/zero
    dummy_info["level"] = 0
    output, ret_code = personal_info.put(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    delete_student(dummy_info["mat_no"])


def test_patch_dets_errors():
    # Modify invalid mat_no
    output, ret_code = personal_info.patch({"mat_no":"INVALIDMAT"})
    assert (output, ret_code) == (None, 404)
    # Patch initialization
    insert_student(row_values)
    dummy_info = info_base.copy()
    # Inserting an extra field
    dummy_info["extra"] = "extra"
    output, ret_code = personal_info.patch(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    dummy_info.pop("extra")
    # Set a required field to empty/None/zero
    dummy_info["level"] = 0
    output, ret_code = personal_info.patch(dummy_info)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    delete_student(dummy_info["mat_no"])


def test_teardown_env():
    test_setup_env()
