from sms.config import db
from sms.models.master import Props, PropsSchema
from sms.src.users import access_decorator

props_dic = {key: 'valuestr' for key in ('ViceChancellor', 'Dean', 'FacultyExamOfficer', 'ChairmanSubCommitteeBCS', 'HOD')}
props_dic.update({'NumPrizeWinners': 'valueint'})


@access_decorator
def get_dynamic_props():
    props = PropsSchema(many=True).dump(Props.query.all())
    dynamic_props = {prop['key']: prop[props_dic[prop['key']]] for prop in props if prop['key'] in props_dic}
    return dynamic_props, 200


@access_decorator
def update_dynamic_props(dynamic_props):
    if any([key for key in dynamic_props if key not in props_dic]):
        return 'Please remove foreign additions', 400
    for key, value in dynamic_props.items():
        prop = Props.query.filter_by(key=key).first()
        setattr(prop, props_dic[prop.key], value)
        db.session.add(prop)
    db.session.commit()
    return 'Update successful', 200
