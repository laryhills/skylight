from sms.src import personal_info
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
