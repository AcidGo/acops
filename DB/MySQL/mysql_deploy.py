# -*- coding: utf8 -*-
# Author: AcidGo

import getpass
import grp
import logging
import pwd
# {% lib-stretch-import %}
from common.Linux.CommandLib import *
from common.Linux.GroupLib import *
from common.Linux.UserLib import *
from common.MySQL.ConfLib import *
from common.OS.OSInfoLib import *
from common.URI.URILib import *

# CONFIG
LOGGING_LEVEL = "info"
# EOF CONFIG

# {% lib-stretch-code %}

class MySQLDeploy(object):
    def __init__(self):
        self.osinfo = OSInfoLib.get_osinfo()
        self.my_pkg_uri = ""
        self.my_cnf_uri = ""
        self.my_cnf_txt = ""
        self.my_dep_cnfpath = ""
        self.my_dep_basedir = ""
        self._basedir_need_create = False
        self.my_dep_user = ""
        self._user_uid = None
        self._user_need_create = False
        self.my_dep_group = ""
        self._group_gid = None
        self._group_need_create = False
        self.db_startup = False

        # only support for Linux
        if self.osinfo.get("platform", {}).get("os", "") != "Linux":
            raise Exception("only support for Linux OS")

    def precheck(self):
        # checking MySQL package uri
        if self.my_pkg_uri and (not URILib.validate(self.my_pkg_uri) or not URILib.access(self.my_pkg_uri)):
            raise Exception("checking pkg uri {!s} is failed".format(self.my_pkg_uri))
        # checking MySQL configure uri and txt
        if self.my_cnf_txt and self.my_cnf_txt:
            raise Exception("cannot use configure uri and configure text in one time")
        if self.my_cnf_uri and (not URILib.validate(self.my_cnf_uri) or not URILib.access(self.my_cnf_uri)):
            raise Exception("checking cnf uri {!s} is failed".format(self.my_cnf_uri))
        # checking MySQL deployment base dir
        if not self.my_dep_basedir:
            raise Exception("checking basedir is empty")
        else:
            if os.path.isfile(self.my_dep_basedir):
                raise Exception("basedir {!s} is a file now".format(self.my_dep_basedir))
            elif os.path.isdir(self.my_dep_basedir) and len(os.listdir(self.my_dep_basedir)) != 0:
                raise Exception("basedir {!s} is a folder and it is not empty".format(self.my_dep_basedir))
            elif not os.path.exists(self.my_dep_basedir):
                self._basedir_need_create = True
        # checking configure path
        if not self.my_dep_cnfpath:
            raise Exception("configure path is empty")
        else:
            if os.path.exists(self.my_dep_cnfpath):
                raise Exception("configure path {!s} is exists".format(self.my_dep_cnfpath))
        # checking user of mysql
        if self.my_dep_user:
            if UserLib.exists(self.my_dep_user):
                logging.info("the user {!s} exists in the Linux".format(self.my_dep_user))
            else:
                logging.info("the user {!s} not exists in the Linux, need to be create".format(self.my_dep_user))
                self._user_need_create = True
        else:
            self.my_dep_user = getpass.getuser()
            logging.warning("not setting the user, so select current user {!s} for using".format(self.my_dep_user))
        self._user_uid = pwd.getpwnam(self.my_dep_user)
        # checking group of mysql
        if self.my_dep_group:
            if GroupLib.exists(self.my_dep_group):
                logging.info("the group {!s} exists in the Linux".format(self.my_dep_group))
            else:
                logging.info("the group {!s} not exists in the Linux, need to be create".format(self.my_dep_group))
                self._group_need_create = True
        else:
            # try using username for group
            self.my_dep_group = self.my_dep_user
            logging.warning("not setting the user, so select username as group {!s} for using".format(self.my_dep_user))
            # checking the group exists
            if not GroupLib.exists(self.my_dep_group):
                raise Exception("selecting group {!s} is not exits".format(self.my_dep_group))
        self._group_gid = grp.getgrnam(self.my_dep_group).gr_gid

    def execute(self):
        # 1. prepare user and group
        if self._group_need_create:
            GroupLib.create(self.my_dep_group)
        if self._user_need_create:
            UserLib.create(self.my_dep_user, primary_group=self.my_dep_group)

        # 2. using pkg uri
        if self._basedir_need_create:
            os.mkdir(self.my_dep_basedir)
            os.chown(self.my_dep_basedir, self._user_uid, self._group_gid)
            logging.info("created basedir {!s}".format(self.my_dep_basedir))
        URILib.move_folder(self.my_pkg_uri, self.my_dep_basedir, decompress=True)

        # 3. fit configure in the file
        if self.my_cnf_uri:
            URILib.move_file(self.my_cnf_uri, self.my_dep_cnfpath)
        else:
            with open(self.my_dep_cnfpath, "w") as f:
                f.write(self.my_cnf_txt)

        # 3. insecure init for mysql
        mysqld_path = ""
        CommandLib.shell([mysqld_path, "--default-files={!s}".format(self.my_dep_cnfpath), "--initialize-insecure"])

        # 4. startup the deploied mysql instance
        if self.db_startup:
            pidfile = ConfLib.get_pidfile(self.my_dep_cnfpath)
            mysqld_safe_path = ""
            CommandLib.shell([mysqld_safe_path, "--default-files={!s}".format(self.my_dep_cnfpath)], background=True)
            time.sleep(10)


