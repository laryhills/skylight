import re
from sms.src import utils
from sms.src import personal_info
from sms.src import course_details
from sms.models.master import Master

start = 2003
stop = 2019
load_session = utils.load_session

def test_personal_info_to_symlink_table():
    for student in Master.query.all():
        db_name = student.database
        if not start <= int(db_name[:4]) <= stop:
            continue
        student_info = personal_info.get(student.mat_no)
        # While we're here assert session admitted matches db_name
        # Also ensures the master entry maps to session db
        assert db_name[:4] == str(student_info["session_admitted"])
        if student_info["is_symlink"]:
            new_session = load_session(student_info["database"])
            # Confirm mat no in Symlink table of new_session
            assert new_session.SymLink.query.filter_by(mat_no=student.mat_no).first().database == db_name


def test_symlink_table_to_personal_info():
    for year in range(start, stop+1):
        session = load_session(year)
        for student in session.SymLink.query.all():
            # Check that symlink DB entry matches Master DB
            assert utils.get_DB(student.mat_no)[:4] == student.database[:4]
            # Check that actual DB entry points back to symlink DB
            assert personal_info.get(student.mat_no)["database"][:4] == str(year)


def test_course_reg_table():
    for student in Master.query.all():
        mat_no = student.mat_no
        if not start <= int(student.database[:4]) <= stop:
            continue
        print (mat_no) # for debugging on failure
        session = load_session(student.database)
        table_blanks = (0,0) # for tracking blanks within tables
        # TODO use new col on table to update to verify value is correct
        for level in range(100, 900, 100):
            course_reg_lvl = eval("session.CourseReg{}".format(level))
            course_reg = course_reg_lvl.query.filter_by(mat_no=mat_no).first()
            if course_reg:
                assert table_blanks != (1, 0) # assert no blank above this table
                table_blanks = (table_blanks[1], 1)
                expected_TCR = 0 # For verifying Total Credits Registered
                for prop in dir(course_reg):
                    if re.match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", prop):
                        if int(course_reg.__getattribute__(prop)):
                            expected_TCR += course_details.get(prop,0)["course_credit"]
                for course in course_reg.carryovers.split(","):
                    # TODO Remove re check after carryover100 set to NULL
                    if re.match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", course):
                        assert course_reg.level >= course_details.get(course,0)["course_level"]
                        expected_TCR += course_details.get(course,0)["course_credit"]
                assert expected_TCR == course_reg.tcr
            elif table_blanks[1]:
                table_blanks = (table_blanks[1], 0) # Met a blank


def test_results_table():
    for student in Master.query.all():
        mat_no = student.mat_no
        if not start <= int(student.database[:4]) <= stop:
            continue
        print (mat_no) # for debugging on failure
        session = load_session(student.database)
        table_blanks = (0,0) # for tracking blanks within tables
        # TODO use new col on table to update to verify value is correct
        for level in range(100, 900, 100):
            result_lvl = eval("session.Result{}".format(level))
            result = result_lvl.query.filter_by(mat_no=mat_no).first()
            if result:
                assert table_blanks != (1, 0) # assert no blank above this table
                table_blanks = (table_blanks[1], 1)
                expected_TCP = 0 # For verifying Total Credits Passed
                for prop in dir(result):
                    if re.match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", prop) and result.__getattribute__(prop):
                        score, grade = result.__getattribute__(prop).split(",")
                        assert utils.compute_grade(int(score), student.database) == grade
                        if grade not in ("F", "ABS"):
                            expected_TCP += course_details.get(prop,0)["course_credit"]
                if result.carryovers:
                    for course, score, grade in [x.split() for x in result.carryovers.split(",")]:
                        assert result.level >= course_details.get(course,0)["course_level"]
                        assert utils.compute_grade(int(score), student.database) == grade
                        if grade not in ("F", "ABS"):
                            expected_TCP += course_details.get(course,0)["course_credit"]
                assert expected_TCP == result.tcp
            elif table_blanks[1]:
                table_blanks = (table_blanks[1], 0) # Met a blank


def test_credits_of_course():
    pass #TODO


def test_grading_rule():
    for year in range(start, stop+1):
        session = load_session(year)
        grades = [x.split() for x in session.GradingRule.query.first().rule.split(",")]
        prev = ("@", 20, 101)
        for grade, point, score  in grades:
            point, score = int(point), int(score)
            # verify ordered sequence
            assert prev[0] < grade
            assert prev[1] > point
            assert prev[2] > score
            assert 0 <= score <= 100 # Ensure scores are between 0 and 100 inc
            prev = (grade, point, score)
