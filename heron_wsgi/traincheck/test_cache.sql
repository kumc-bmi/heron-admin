PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE "GRADEBOOK" (
	"intCompletionReportID" INTEGER, 
	"intInstitutionID" INTEGER, 
	"strCompletionReport" VARCHAR(120), 
	"intGroupID" INTEGER, 
	"strGroup" VARCHAR(120), 
	"intStageID" INTEGER, 
	"strStage" VARCHAR(120)
);
INSERT INTO "GRADEBOOK" VALUES(27,44,'sst',74,'ssttt',104,'ssttttt');
INSERT INTO "GRADEBOOK" VALUES(134,151,'ssssttt',181,'ssssttttt',211,'ssss');
INSERT INTO "GRADEBOOK" VALUES(241,258,'sttttt',288,'s',318,'stt');
CREATE TABLE "MEMBERS" (
	"intMemberID" INTEGER, 
	"strLastII" VARCHAR(120), 
	"strFirstII" VARCHAR(120), 
	"strUsernameII" VARCHAR(120), 
	"strInstUsername" VARCHAR(120), 
	"strInstEmail" VARCHAR(120), 
	"dteAdded" VARCHAR(120), 
	"dteAffiliated" VARCHAR(120), 
	"dteLastLogin" VARCHAR(120), 
	"strCustom1" VARCHAR(120), 
	"strCustom2" VARCHAR(120), 
	"strCustom3" VARCHAR(120), 
	"strCustom4" VARCHAR(120), 
	"strCustom5" VARCHAR(120), 
	"strSSOCustomAttrib1" VARCHAR(120), 
	"strSSOCustomAttrib2" VARCHAR(120), 
	"strEmployeeNum" VARCHAR(120)
);
INSERT INTO "MEMBERS" VALUES(27,'ttttt','ssstttt','sttt','sssstt','sst',NULL,'ssstttttt','sttttt','sssstttt','ssttt','tt','ssst','s','sssstttttt','ssttttt','tttt');
INSERT INTO "MEMBERS" VALUES(252,'tttttt','sssttttt','stttt','ssssttt','sstt','t','sss','stttttt','ssssttttt','sstttt','ttt','ssstt','st','ssss','sstttttt','ttttt');
INSERT INTO "MEMBERS" VALUES(477,NULL,'ssstttttt','sttttt','sssstttt','ssttt','tt','ssst','s','sssstttttt','ssttttt','tttt','sssttt','stt','sssst','ss','tttttt');
INSERT INTO "MEMBERS" VALUES(702,'t','sss','stttttt','ssssttttt','sstttt','ttt','ssstt','st','ssss','sstttttt','ttttt','ssstttt','sttt','sssstt','sst',NULL);
CREATE TABLE "CRS" (
	"CR_InstitutionID" INTEGER, 
	"MemberID" INTEGER, 
	"EmplID" VARCHAR(120), 
	"StudentID" INTEGER, 
	"InstitutionUserName" VARCHAR(120), 
	"FirstName" VARCHAR(120), 
	"LastName" VARCHAR(120), 
	"memberEmail" VARCHAR(120), 
	"AddedMember" VARCHAR(120), 
	"strCompletionReport" VARCHAR(120), 
	"intGroupID" INTEGER, 
	"strGroup" VARCHAR(120), 
	"intStageID" INTEGER, 
	"intStageNumber" INTEGER, 
	"strStage" VARCHAR(120), 
	"intCompletionReportID" INTEGER, 
	"intMemberStageID" INTEGER, 
	"dtePassed" VARCHAR(120), 
	"intScore" INTEGER, 
	"intPassingScore" INTEGER, 
	"dteExpiration" VARCHAR(120)
);
INSERT INTO "CRS" VALUES(27,44,'sst',74,'ssttt','tt','ssst','s','2000-12-06','sss',185,'ssstt',215,232,NULL,262,279,'2000-09-06',325,342,'2000-12-06');
INSERT INTO "CRS" VALUES(388,405,'sssttttt',435,'sss','stttttt','ssssttttt','sstttt','2000-01-09','sssstttt',546,'sssstttttt',576,593,'stttt',623,640,'2000-10-09',686,703,'2000-01-09');
INSERT INTO "CRS" VALUES(749,766,'sssstt',796,'sssstttt','ssttt','tt','ssst','2000-02-12','t',907,'ttt',937,954,'sst',984,1001,'2000-11-12',1047,1064,'2000-02-12');
INSERT INTO "CRS" VALUES(1110,1127,'tttttt',1157,'t','sss','stttttt','ssssttttt','2000-03-15','sttttt',1268,'s',1298,1315,'sssttttt',1345,1362,'2000-12-15',1408,1425,'2000-03-15');
INSERT INTO "CRS" VALUES(1471,1488,'sttt',1518,'sttttt','sssstttt','ssttt','tt','2000-04-18','sstt',1629,'sstttt',1659,1676,'sssstt',1706,1723,'2000-01-18',1769,1786,'2000-04-18');
INSERT INTO "CRS" (MemberID, intScore, strCompletionReport, InstitutionUserName)
VALUES('123','96','Human Subjects Research','bob');
COMMIT;
