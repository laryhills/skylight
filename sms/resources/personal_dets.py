from json import dumps
from sms.resources import personal_info
from sms.resources.users import access_decorator


@access_decorator
def get(mat_no):
    return personal_info.get(mat_no), 200


@access_decorator
def post(data):
    output = personal_info.post(data)
    if output:
        return output, 400
    return None, 200
