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

sql_all_courses = "SELECT * FROM courses"
sql_get_course = lambda course: ("SELECT * FROM courses WHERE course_code=?", (course,))
sql_get_level = ("SELECT * FROM courses WHERE course_level=? AND active=?", (level, 1))
sql_all_courses_active = ("SELECT * FROM courses WHERE active=?",(1,))


def test_get_one_course():
    course_obj = course_details.get(valid_course)
    course_row = cur.execute(*sql_get_course(valid_course)).fetchone()
    assert course_obj["teaching_dept"] == course_row["teaching_department"]
    for prop in set(course_keys) - {"teaching_department"}:
        assert course_obj[prop] == course_row[prop]

def test_get_all_level():
    lvl_courses = course_details.get_all(level, True, False)
    lvl_courses_row = cur.execute(*sql_get_level).fetchall()
    lvl_codes = set([x["course_code"] for x in lvl_courses_row])
    for course in lvl_courses:
       lvl_codes.remove(course["course_code"])
    assert len(lvl_codes) == 0


def test_get_all_options():
    all_options = set([x["course_code"] for x in course_details.get_all(level, True, False)])
    one_option = set([x["course_code"] for x in course_details.get_all(level, False, False)])
    diff = len(all_options - one_option)
    diff_row = [x for x in cur.execute(*sql_get_level).fetchall() if x["options"] != 0]
    options = len(set([x["options"] for x in diff_row]))
    assert diff == len(diff_row) - options


def test_get_all_default():
    all_courses = course_details.get_all(None, True, False)
    sql_all_courses = cur.execute(*sql_all_courses_active).fetchall()
    assert len(sql_all_courses) == len(all_courses)


def test_get_all_inc_inactive():
    pass 
