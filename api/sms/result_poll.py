from sms.config import db
from sms import master_poll

lastLoaded = None

def get(mat_no, level=None):
    db_name = master_poll.getDB(mat_no)[:-3]

    ans='['
    exec('from sms.models import _{}'.format(db_name))
    levels = [level] if level else range(100,900,100)
    for level in levels:
        resLvl = eval('_{}.Result{}.query.filter_by(mat_no=mat_no).first()'.format(db_name,level))
        resStr = eval('_{}.Result{}Schema().dumps(resLvl)'.format(db_name,level))
        ans+=(resStr+',')
    return ans[:-1]+']'
