import os
import sqlite3
from tests import db_path
from sms.src import course_details

conn = sqlite3.connect(os.path.join(db_path, "courses.db"))
conn.row_factory = sqlite3.Row
cur = conn.cursor()
level = 500
valid_course = "MEE321"
course_keys = ("course_code", "course_title", "course_credit", "course_semester", "course_level", "teaching_department", "start_date", "end_date", "options", "active")
inv_crs_val = ("INV211", "Invalid Course", 2, 1, 200, "MEE", 1970, 2999, 0, 0)

sql_all_courses = "SELECT * FROM courses"
sql_get_course = lambda course=valid_course: ("SELECT * FROM courses WHERE course_code=?", (course,))
sql_get_level = lambda level=level: ("SELECT * FROM courses WHERE course_level=? AND active=?", (level, 1))
sql_all_courses_active = ("SELECT * FROM courses WHERE active=?",(1,))
sql_ins_inactive = ("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?)", inv_crs_val)
sql_del_course = lambda course=inv_crs_val[0]: ("DELETE FROM courses WHERE course_code=?",(course,))


def test_setup_env():
    cur.execute(*sql_del_course())
    conn.commit()


def test_get_one_course():
    course_obj = course_details.get(valid_course)
    course_row = cur.execute(*sql_get_course(valid_course)).fetchone()
    assert course_obj["teaching_dept"] == course_row["teaching_department"]
    for prop in set(course_keys) - {"teaching_department"}:
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
    cur.execute(*sql_ins_inactive)
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
    course_add["teaching_dept"] = course_add["teaching_department"]
    course_add.pop("teaching_department")
    assert course_details.post(course_add) == (None, 200)
    assert course_details.post(course_add)[1] == 400
    cur.execute(*sql_del_course())
    conn.commit()


def test_teardown_env():
    test_setup_env()
