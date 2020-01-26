from json import dumps
from sys import modules
from sms.config import db
from sms import utils
from importlib import reload

lastLoaded = None

def get(mat_no, level=None):
    #Get db file for student
    db_name = utils.getDB(mat_no)[:-3]
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    exec('from sms.models import _{}'.format(db_name))
    if ('sms.models._{}'.format(db_name) in modules) and (lastLoaded!=db_name):
        exec('reload(_{})'.format(db_name))
    lastLoaded = db_name
    #Get result for all levels if none else for level
    ans=[]
    levels = [level] if level else range(100,900,100)
    for level in levels:
        resLvl = eval('_{}.Result{}.query.filter_by(mat_no=mat_no).first()'.format(db_name,level))
        resStr = eval('_{}.Result{}Schema().dump(resLvl)'.format(db_name,level))
        ans.append(resStr)
    return dumps(ans)
