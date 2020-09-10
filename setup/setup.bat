ECHO ON

del %USERPROFILE%\PycharmProjects\skylight\sms\database\master.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\courses.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2003-2004.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2004-2005.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2005-2006.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2006-2007.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2007-2008.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2008-2009.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2009-2010.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2010-2011.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2011-2012.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2012-2013.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2013-2014.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2014-2015.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2015-2016.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2016-2017.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2017-2018.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2018-2019.db
del %USERPROFILE%\PycharmProjects\skylight\sms\database\2019-2020.db


cd "%USERPROFILE%\PycharmProjects\skylight\setup\src"

pip install numpy pandas

python generate_models.py
python personal_info.py
python course_details.py
python "generate_courses_and_credits.py"
python "generate_course_reg_and_result.py"
python "generate_grading_rule.py"
python "generate_categories.py"
python "generate_degree_class.py"

cd "%USERPROFILE%\PycharmProjects\skylight"

