from json import dumps
from sms import utils


def get(mat_no, level=None):
    #Get result for all levels if none else for level
    db_name = utils.get_DB(mat_no)[:-3]
    session = utils.load_session(db_name)
    ans=[]
    levels = [level] if level else range(100,900,100)
    for level in levels:
        resLvl = eval('session.Result{}.query.filter_by(mat_no=mat_no).first()'.format(level))
        resStr = eval('session.Result{}Schema().dump(resLvl)'.format(level))
        ans.append(resStr)
    return dumps(ans)
