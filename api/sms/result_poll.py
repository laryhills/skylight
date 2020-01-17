from flask import abort
from sms.config import db
from json import loads
from sms.models.master import Master, MasterSchema
#from sms.models._2013_2014 import *

def get(mat_no=None, level=None):
    if mat_no:
        # Lookup the student's details in the master db
        student = Master.query.filter_by(mat_no=mat_no).first_or_404()
        master_schema = MasterSchema()
        db_name = master_schema.dump(student)['database']
        db_name = db_name.replace('-', '_')

        ans=[]
        exec('from sms.models._{} import *'.format(db_name[:-3]))
        print (locals()['Result100'].__bind_key__)
        if level == None:
            for level in range(100,900,100):
                try:
                    resLvl = eval('Result{}.query.filter_by(mat_no=mat_no).first()'.format(level))
                    resStr = eval('Result{}Schema().dumps(resLvl)'.format(level))
                    ans.append(loads(resStr))
                except Exception:
                    ans.append({})
        else:
            try:
                resLvl = eval('Result{}.query.filter_by(mat_no=mat_no).first()'.format(level))
                resStr = eval('Result{}Schema().dumps(resLvl)'.format(level))
                ans.append(loads(resStr))
            except Exception:
                ans.append({})
        print(ans)
