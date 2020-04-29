from sms.users import access_decorator, fn_props
from sms.models.logs import Logs
from json import loads


@access_decorator
def get(limit = 5, offset = 0):
    log_size = Logs.query.count()
    offset = log_size - limit - offset
    if offset < 0:
        return [[]]
    log_list = Logs.query.offset(offset).limit(limit).all()
    return [(log.timestamp, fn_props[log.operation]["logs"](log.user, loads(log.params))) for log in log_list]
