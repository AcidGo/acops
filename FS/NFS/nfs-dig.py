# -*- coding: utf8 -*-
# Author: AcidGo

import logging
# {% lib-stretch-import %}

from common.OSInfoLib import *
from common.RPCInfoLib import *
from common.TCPLib import *
from common.VFSLib import *

# CONFIG
LOGGING_LEVEL = "info"
# EOF CONFIG

# {% lib-stretch-code %}

class NFSDig(object):
    def __init__(self):
        self.osinfo = OSInfoLib.get_osinfo()
        self.nfs_hosts = []
        self.fstab = {}
        self.ok = True

        # only support for Linux
        if self.osinfo.get("platform", {}).get("os", "") != "Linux":
            raise Exception("only support for Linux OS")

        self.find_nfs_target()

    def add_nfs_target(self, nfs_hosts):
        for i in nfs_hosts.split(","):
            if i:
                self.nfs_hosts.append(i.strip())

    def find_nfs_target(self):
        fstab_file = "/etc/fstab"
        self.fstab = {k: v for k, v in VFSLib.parse_fstab(fstab_file).items() if v.get("fs_type", "").startswith("nfs")}

        for fs_spec in self.fstab:
            self.nfs_hosts.append(fs_spec.split(":", 1)[0])

    def precheck(self):
        return

    def execute(self):
        # 1. check nfs is mounted on the host
        logging.info("checking nfs is moutned on the host ......")
        nfs_not_mounted = {}
        mounted_fs = VFSLib.get_mounted()
        logging.debug("mounted_fs: {!s}".format(str(mounted_fs)))

        for fs_spec, fs_args in self.fstab.items():
            if fs_spec not in mounted_fs:
                nfs_not_mounted[fs_spec] = fs_args
                continue
            if not mounted_fs[fs_spec].get("fs_type", "").startswith("nfs"):
                nfs_not_mounted[fs_spec] = fs_args
                continue

        if len(nfs_not_mounted) > 0:
            logging.error("found not mounted nfs!")
            self.ok = False
            for fs_spec, fs_args in nfs_not_mounted.items():
                lst = [fs_spec] + [v for v in fs_args.values()]
                logging.error("not mounted: " + "\t".join(lst))

        for fs_spec, fs_args in mounted_fs.items():
            if fs_args.get("fs_type", "").startswith("nfs") and fs_spec not in nfs_not_mounted:
                lst = [fs_spec] + [v for v in fs_args.values()]
                logging.info("the nfs target has been mounted: " + "\t".join(lst))

        if len(nfs_not_mounted) == 0:
            logging.info("all nfs target in fstab has been mounted")

        # 2. check nfs network is accessed
        logging.info("checking nfs network(tcp) is accessed ......")
        for h in self.nfs_hosts:
            # 2.1 check rpc port is accessed
            if not TCPLib.tcp_test(h, 111):
                self.ok = False
                logging.error("cannot access remote {!s} rpc port {!s}".format(h, 111))
                continue

            logging.info("can accessed remote {!s} rpc port {!s}".format(h, 111))

            # 2.2 check nfs portmap service is accessed, only tcp
            nfs_svc_set = {
                RPCInfoLib.RPC_SVC_MOUNTD: "mountd",
                RPCInfoLib.RPC_SVC_NFS_ACL: "nfs_acl",
                RPCInfoLib.RPC_SVC_NFS: "nfs",
                RPCInfoLib.RPC_SVC_NLOCKMGR: "nlockmgr",
                RPCInfoLib.RPC_SVC_STATUS: "status",
            }
            rpc_res_lst = RPCInfoLib.get_finger(h)
            if len(rpc_res_lst) <= 0:
                self.ok = False
                logging.error("response of rpc request is empty from {!s}".format(h))
                continue
            tested_ports = set()
            for rpc_res in rpc_res_lst:
                if rpc_res["program"] not in nfs_svc_set or rpc_res["protocol"].endswith("udp") or rpc_res["port"] in tested_ports:
                    continue
                logging.debug("rpc_res: {!s}".format(rpc_res))
                tested_ports.add(rpc_res["port"])
                if not TCPLib.tcp_test(h, rpc_res["port"]):
                    self.ok = False
                    logging.error("cannot access remote {!s} rpc service {!s} with TCP".format(h, nfs_svc_set[rpc_res["program"]]))
                else:
                    logging.info("can access remote {!s} rpc service {!s} with TCP".format(h, nfs_svc_set[rpc_res["program"]]))

        logging.info("all done")

    def postcheck(self):
        return

def init_logger(level, logfile=None):
    """日志功能初始化。
    如果使用日志文件记录，那么则默认使用 RotatinFileHandler 的大小轮询方式，
    默认每个最大 10 MB，最多保留 5 个。
    Args:
        level: 设定的最低日志级别。
        logfile: 设置日志文件路径，如果不设置则表示将日志输出于标准输出。
    """
    import os
    import sys
    if not logfile:
        logging.basicConfig(
            level = getattr(logging, level.upper()),
            format = "%(asctime)s [%(levelname)s] %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S"
        )
    else:
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))

        if logfile.lower() == "local":
            logfile = os.path.join(sys.path[0], os.path.basename(os.path.splitext(__file__)[0]) + ".log")

        handler = RotatingFileHandler(logfile, maxBytes=10*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logging.debug("Logger init finished.")

if __name__ == '__main__':
    # ########## Self Test
    INPUT_REMOTE_HOSTS = ""
    # ########## EOF Self Test

    init_logger(LOGGING_LEVEL)

    nfs_dig = NFSDig()
    if INPUT_REMOTE_HOSTS:
        nfs_dig.add_nfs_target(INPUT_REMOTE_HOSTS)
    nfs_dig.precheck()
    nfs_dig.execute()
    nfs_dig.postcheck()

    if nfs_dig.ok is False:
        raise Exception("result has error, please check it")