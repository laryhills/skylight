import re
from sms.src import personal_info
from sms.src import course_details
from sms.models.master import Master
from sms.src.utils import get_DB, load_session

start = 2003
stop = 2019

def test_master_to_session_map():
    for student in Master.query.all():
        assert personal_info.get(student.mat_no) != None


def test_personal_info_to_symlink_table():
    for student in Master.query.all():
        db_name = student.database
        student_info = personal_info.get(student.mat_no)
        # While we're here assert session admitted matches db_name
        assert db_name[:4] == str(student_info["session_admitted"])
        if student_info["is_symlink"]:
            new_session = load_session(student_info["database"])
            # Confirm mat no in Symlink table of new_session
            assert new_session.SymLink.query.filter_by(mat_no=student.mat_no).first().database == db_name


def test_symlink_table_to_personal_info():
    for year in range(start, stop+1):
        session = load_session(year)
        for student in session.SymLink.query.all():
            assert get_DB(student.mat_no)[:4] == student.database[:4]
            assert personal_info.get(student.mat_no)["database"][:4] == str(year)

# TODO test all grad_stats level == -1

def test_levels():
    pass #for student in Master.query.all():
    pass #    db_name = get_DB(student.mat_no)
    pass #    student_info = personal_info.get(student.mat_no)


def test_tcr():
    for student in Master.query.all():
        mat_no = student.mat_no
        print (mat_no)
        session = load_session(student.database)
        # TODO use new col to know table to stop
        for level in range(100, 900, 100):
            course_reg_lvl = eval("session.CourseReg{}".format(level))
            course_reg = course_reg_lvl.query.filter_by(mat_no=mat_no).first()
            if course_reg:
                expected_TCR = 0
                for prop in dir(course_reg):
                    if re.match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", prop):
                        if int(course_reg.__getattribute__(prop)):
                            expected_TCR += course_details.get(prop,0)["course_credit"]
                for course in course_reg.carryovers.split(","):
                    if re.match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", course):
                        expected_TCR += course_details.get(course,0)["course_credit"]
                assert expected_TCR == course_reg.tcr


def test_tcp():
    for student in Master.query.all():
        mat_no = student.mat_no
        print (mat_no)
        session = load_session(student.database)
        # TODO use new col to know table to stop
        for level in range(100, 900, 100):
            result_lvl = eval("session.Result{}".format(level))
            result = result_lvl.query.filter_by(mat_no=mat_no).first()
            if result:
                expected_TCP = 0
                for prop in dir(result):
                    if re.match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", prop) and result.__getattribute__(prop):
                        grade = result.__getattribute__(prop).split(",")[1]
                        if grade not in ("F", "ABS"):
                            expected_TCP += course_details.get(prop,0)["course_credit"]
                if result.carryovers:
                    for course, score, grade in [x.split() for x in result.carryovers.split(",")]:
                        if grade not in ("F", "ABS"):
                            expected_TCP += course_details.get(course,0)["course_credit"]
                assert expected_TCP == result.tcp
