from sms.src.users import fn_props
from sms.models.logs import Logs
from json import loads
from sms.config import db
from sms.src.users import access_decorator


# todo: implement access controls w/o logging
# @access_decorator
def get(limit=5, offset=0):
    log_size = Logs.query.count()
    offset = log_size - limit - offset
    if offset < 0:
        if limit == 15:
            # Acts as an EOF for the scrolling effect in the frontend which sends a query with limit = 15
            return [[]]
        else:
            offset = 0
    log_list = Logs.query.offset(offset).limit(limit).all()
    return [(log.timestamp, fn_props[log.operation]["logs"](log.user, loads(log.params))) for log in log_list]


@access_decorator
def delete(ids):
    logs = []
    for _id in ids:
        logs.append(Logs.query.filter_by(id=_id).first())
    if all(logs):
        for log in logs:
            db.session.delete(log)
        db.session.commit()
    else:
        return None, 404
    return None, 200


@access_decorator
def delete_all():
    Logs.query.delete()
    db.session.commit()
    return None, 200
