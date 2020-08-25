import os
import sqlite3
from tests import db_path
from sms.src import course_details

conn = sqlite3.connect(os.path.join(db_path, "courses.db"))
conn.row_factory = sqlite3.Row
cur = conn.cursor()
level = 500
valid_course = "MEE321"
course_keys = ("course_code", "course_title", "course_credit", "course_semester", "course_level", "teaching_dept", "start_date", "end_date", "options", "active")
inv_crs_val = ("INV211", "Invalid Course", 2, 1, 200, "MEE", 1970, 2999, 0, 0)
inv_crs_val_2 = ("INV311", "Invalid Course-2", 2, 1, 300, "MEE", 1970, 2999, 0, 0)

sql_all_courses = "SELECT * FROM courses"
sql_get_course = lambda course=valid_course: ("SELECT * FROM courses WHERE course_code=?", (course,))
sql_get_level = lambda level=level: ("SELECT * FROM courses WHERE course_level=? AND active=?", (level, 1))
sql_all_courses_active = ("SELECT * FROM courses WHERE active=?",(1,))
sql_ins_course = lambda course=inv_crs_val: ("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?)", (*course,))
sql_del_course = lambda course=inv_crs_val[0]: ("DELETE FROM courses WHERE course_code=?",(course,))


def test_setup_env():
    cur.execute(*sql_del_course())
    cur.execute(*sql_del_course(inv_crs_val_2[0]))
    conn.commit()


def test_get_one_course():
    course_obj = course_details.get(valid_course)
    course_row = cur.execute(*sql_get_course(valid_course)).fetchone()
    for prop in set(course_keys):
        assert course_obj[prop] == course_row[prop]


def test_get_all_level():
    lvl_courses = course_details.get_all(level, True, False)
    lvl_courses_row = cur.execute(*sql_get_level()).fetchall()
    lvl_codes = set([x["course_code"] for x in lvl_courses_row])
    for course in lvl_courses:
       lvl_codes.remove(course["course_code"])
    assert len(lvl_codes) == 0


def test_get_all_options():
    all_options = set([x["course_code"] for x in course_details.get_all(level, True, False)])
    one_option = set([x["course_code"] for x in course_details.get_all(level, False, False)])
    diff = len(all_options - one_option)
    diff_row = [x for x in cur.execute(*sql_get_level()).fetchall() if x["options"] != 0]
    options = len(set([x["options"] for x in diff_row]))
    assert diff == len(diff_row) - options


def test_get_all_default():
    all_courses = course_details.get_all()
    sql_all_courses = cur.execute(*sql_all_courses_active).fetchall()
    assert len(sql_all_courses) == len(all_courses)


def test_get_all_inactive():
    cur.execute(*sql_ins_course())
    conn.commit()
    curr_actives = set([x["course_code"] for x in course_details.get_all(None, True, False)])
    curr_all = set([x["course_code"] for x in course_details.get_all(None, True, True)])
    curr_inactives = curr_all - curr_actives
    assert inv_crs_val[0] in curr_inactives
    cur.execute(*sql_del_course())
    conn.commit()


def test_get_course_details():
    assert course_details.get_course_details(valid_course) == ([course_details.get(valid_course)], 200)
    assert course_details.get_course_details(inv_crs_val[0]) == (None, 404)
    assert course_details.get_course_details() == (course_details.get_all(), 200)


def test_post():
    course_add = dict(zip(course_keys, inv_crs_val))
    assert course_details.post(course_add) == (None, 200)
    assert course_details.post(course_add)[1] == 400
    cur.execute(*sql_del_course())
    conn.commit()


def test_delete():
    assert course_details.delete(inv_crs_val[0]) == (None, 404)
    cur.execute(*sql_ins_course())
    conn.commit()
    assert course_details.delete(inv_crs_val[0]) == (None, 200)
    course_row = cur.execute(*sql_get_course(inv_crs_val[0])).fetchone()
    assert course_row == None


def test_put_one():
    course_add = dict(zip(course_keys, inv_crs_val))
    course_add["course_credit"] = 3
    course_add["course_semester"] = 2
    course_list = [course_add]
    assert course_details.put(course_list) == (None, 404)
    cur.execute(*sql_ins_course())
    conn.commit()
    assert course_details.put(course_list) == (None, 200)
    course_row = cur.execute(*sql_get_course(inv_crs_val[0])).fetchone()
    assert course_row["course_credit"] == 3
    assert course_row["course_semester"] == 2
    cur.execute(*sql_del_course())
    conn.commit()


def test_put_mult():
    course_add = dict(zip(course_keys, inv_crs_val))
    course_add["course_credit"] = 3
    course_add["course_semester"] = 2
    course_add_2 = dict(zip(course_keys, inv_crs_val_2))
    course_add_2["start_date"] = 2012
    course_add_2["options"] = 3
    course_list = [course_add, course_add_2]
    cur.execute(*sql_ins_course())
    conn.commit()
    assert course_details.put(course_list) == (None, 404)
    course_row = cur.execute(*sql_get_course(inv_crs_val[0])).fetchone()
    assert course_row["course_credit"] != 3
    assert course_row["course_semester"] != 2
    cur.execute(*sql_ins_course(inv_crs_val_2))
    conn.commit()
    assert course_details.put(course_list) == (None, 200)
    course_row = cur.execute(*sql_get_course(inv_crs_val[0])).fetchone()
    assert course_row["course_credit"] == 3
    assert course_row["course_semester"] == 2
    course_row = cur.execute(*sql_get_course(inv_crs_val_2[0])).fetchone()
    assert course_row["start_date"] == 2012
    assert course_row["options"] == 3
    cur.execute(*sql_del_course())
    cur.execute(*sql_del_course(inv_crs_val_2[0]))
    conn.commit()


def test_teardown_env():
    test_setup_env()
