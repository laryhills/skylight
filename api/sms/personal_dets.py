from json import dumps
from sms import personal_info
from sms.users import access_decorator


@access_decorator
def get(mat_no):
    return dumps(personal_info.get(mat_no)), 200


@access_decorator
def post(data):
    return personal_info.post(data), 200
