BEGIN TRANSACTION;
CREATE TABLE "Props" (
	`KEY`	TEXT,
	`VALUESTR`	TEXT,
	`VALUEINT`	INTEGER,
	PRIMARY KEY(KEY)
);
INSERT INTO `Props` VALUES ('GradingRule','A 5 70,B 4 60,C 3 50,D 2 45,E 1 40,F 0 0,ABS 0 -1',NULL);
INSERT INTO `Props` VALUES ('CurrentSession',NULL,2019);
INSERT INTO `Props` VALUES ('MaxRegCredits',NULL,50);
INSERT INTO `Props` VALUES ('CondMaxRegCredits500',NULL,51);
INSERT INTO `Props` VALUES ('DBWriteCounter',NULL,148);
INSERT INTO `Props` VALUES ('SessionList','[2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019]',NULL);
INSERT INTO `Props` VALUES ('DegreeClass','First_class_honours 4.5 5.0,Second_class_honours_(upper) 3.5 4.4999,Second_class_honours_(lower) 2.4 3.4999,Third_class_honours 1.5 2.3999,Pass 1.0 1.4999,Fail 0.0 0.9999',NULL);
INSERT INTO `Props` VALUES ('ResultEdit',NULL,1);
INSERT INTO `Props` VALUES ('LevelPercent','10 15 20 25 30,10 20 30 40,25 35 40',NULL);
INSERT INTO `Props` VALUES ('Department','["MEE", "MECHANICAL ENGINEERING"]',NULL);
INSERT INTO `Props` VALUES ('NumPrizeWinners', NULL, 1);
INSERT INTO `Props` VALUES ('ViceChancellor', NULL, NULL);
INSERT INTO `Props` VALUES ('Dean', NULL, NULL);
INSERT INTO `Props` VALUES ('FacultyExamOfficer', NULL, NULL);
INSERT INTO `Props` VALUES ('ChairmanSubCommitteeBCS', NULL, NULL);
INSERT INTO `Props` VALUES ('HOD', NULL, NULL);
COMMIT;
