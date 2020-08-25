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

python3 generate_models.py
python3 personal_info.py
python3 course_details.py
python3 "generate_courses_&_credits.py"
python3 "generate_course_reg_&_result.py"
python3 "generate_grading_rule.py"
python3 "generate_categories.py"
python3 "generate_degree_class.py"

cd "%USERPROFILE%\PycharmProjects\skylight"

