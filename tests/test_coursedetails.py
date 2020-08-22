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


def get_course(course):
    return cur.execute("SELECT * FROM courses WHERE course_code=?",(course,)).fetchone()


def get_level(level):
    return cur.execute("SELECT * FROM courses WHERE course_level=? AND active=?",(level, 1)).fetchall()


def test_get_one_course():
    course_obj = course_details.get(valid_course)
    course_row = get_course(valid_course)
    assert course_obj["teaching_dept"] == course_row["teaching_department"]
    for prop in set(course_keys) - {"teaching_department"}:
        assert course_obj[prop] == course_row[prop]

def test_get_all_level():
    lvl_courses = course_details.get_all(level, options=True, inactive=False)
    lvl_courses_row = get_level(level)
    lvl_codes = set([x["course_code"] for x in lvl_courses_row])
    for course in lvl_courses:
       lvl_codes.remove(course["course_code"])
    assert len(lvl_codes) == 0


def test_get_all_level_options():
    all_options = set([x["course_code"] for x in course_details.get_all(level, options=True, inactive=False)])
    one_option = set([x["course_code"] for x in course_details.get_all(level, options=False, inactive=False)])
    diff = len(all_options - one_option)
    diff_row = [x for x in get_level(level) if x["options"] != 0]
    options = len(set([x["options"] for x in diff_row]))
    assert diff == len(diff_row) - options
