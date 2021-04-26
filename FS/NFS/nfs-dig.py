# -*- coding: utf8 -*-
# Author: AcidGo

from common.OSInfoLib import *

class NFSDig(object):
    def __init__(self):
        self.osinfo = OSInfoLib.get_osinfo()
        self.nfs_hosts = []

        # 

    def add_nfs_target(self, nfs_hosts):
        for i in nfs_hosts.split(","):
            self.nfs_hosts.append(i.strip())

    def find_nfs_target(self):
        mount_file = "/etc/"

