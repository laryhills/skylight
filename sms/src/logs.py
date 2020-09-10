from json import loads
from sms.config import db
from sqlalchemy import desc
from sms.models.logs import Logs
from sms.models.user import User
from sms.src.users import fn_props
from sms.src.users import access_decorator

# todo: implement access controls w/o logging
# @access_decorator
def get(step=0, title=None, time=None, count=15):
    query = Logs.query.order_by(desc(Logs.id))
    if title:
        user = User.query.filter_by(title=title).first()
        if user:
            query = query.filter_by(user=user.username)
    if time:
        query = query.filter(Logs.timestamp >= time)

    log_list = query.offset(step * count).limit(count).all()
    return [(log.timestamp, fn_props[log.operation]["logs"](log.user, loads(log.params))) for log in log_list]


@access_decorator
def delete(ids=()):
    if not ids:
        Logs.query.delete()
        db.session.commit()
        return None, 200
    logs = []
    for _id in ids:
        logs.append(Logs.query.filter_by(id=_id).first())
    if all(logs):
        for log in logs:
            db.session.delete(log)
        db.session.commit()
        return None, 200
    return None, 404
