from sms import personal_info
from sms.users import access_decorator


@access_decorator
def get(mat_no, ret_JSON=True):
    return personal_info.get(mat_no, ret_JSON)


@access_decorator
def post(student_data):
    return personal_info.post(student_data)
