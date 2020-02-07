import os
import sqlite3
from sms import course_reg
from sms import utils
from sms import result_statement

db_base_dir = os.path.join(os.path.dirname(__file__), 'sms', 'database')
print ("DB path",os.path.join(db_base_dir, 'master.db'))
conn = sqlite3.connect(os.path.join(db_base_dir, 'master.db'))
for row in conn.execute("SELECT MATNO from Main").fetchall():
	mat_no = row[0]
	print (mat_no)
	if mat_no>="ENG1100000":
		try:
			if (utils.get_level(mat_no,1) != 600) and result_statement.get(mat_no, 0)["results"]:
				print ("working on",mat_no)
				course_reg.get(mat_no)
				print ("done with",mat_no)
			else:
				print ("Graduated if < ENG11 else no exam record for",mat_no)
		except Exception:
			print ("some error with", mat_no)
