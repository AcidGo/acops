# Author: AcidGo

class VFSLib(object):
    @staticmethod
    def parse_fstab(file_path):
        """
            {
                "/dev/sda1": {
                    "fs_file": "/",
                    "fs_type": "ext4",
                    "fs_options": "defaults",
                    "fs_dump": "1",
                    "fs_pass": "1",
                },
            }
        """
        res = {}
        with open(file_path, "r") as f:
            for line in f:
                if line.strip().startswith("#"):
                    continue
                lst = line.split()
                if len(lst) != 6:
                    continue
                res[lst[0]] = {
                    "fs_file": lst[1],
                    "fs_type": lst[2],
                    "fs_options": lst[3],
                    "fs_dump": lst[4],
                    "fs_pass": lst[5],
                }
        return res

    @staticmethod
    def get_mounted(is_all=False):
        """
            {
                "/dev/sda1": {
                    "fs_file": "/",
                    "fs_type": "ext4",
                    "fs_options": "rw,relatime,attr2,inode64,noquota",
                    "fs_dump": "0",
                    "fs_pass": "0",
                }
            }
        """
        mounted_file = "/proc/mount"
        ignore_fs = {
            "rootfs", "sysfs", "proc", "devtmpfs", "securityfs", 
            "tmpfs", "devpts", "cgroup", "pstore", "configfs", 
            "autofs", "debugfs", "hugetlbfs", "mqueue",
        }

        res = {}
        with open(mounted_file, "r") as f:
            for line in f:
                lst = line.strip().split()
                if len(lst) != 6:
                    continue
                if is_all is False and lst[2] in ignore_fs:
                    continue
                rse[lst[0]] = {
                    "fs_file": lst[1],
                    "fs_type": lst[2],
                    "fs_options": lst[3],
                    "fs_dump": lst[4],
                    "fs_pass": lst[5],
                }

        return res