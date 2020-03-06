from sms.config import db
#from sms.users import access_decorator, fn_props
from sms.models.logs import Logs, LogsSchema
from json import loads


#def get(limit = 20):
#    log_list = Logs.query.limit(limit).all()
#    return [(log.timestamp, fn_props[log.operation]["logs"](log.user, loads(log.params))) for log in log_list]


def post(log_data):
    '''log_data = {"timestamp": 1234,
                   "operation": "personal_info.get",
                   "user": "ucheigbeka",
                   "params": "{"mat_no": "ENG1503917",
                               "something": "other_thing"}
                  }'''
    log_record = LogsSchema().load(log_data)
    db.session.add(log_record)
    db.session.commit()
