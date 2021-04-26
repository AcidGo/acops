# -*- coding: utf8 -*-
# Author: AcidGo

import os
import platform

class OSInfoLib(object):
    @staticmethod
    def get_osinfo():
        s = platform.system()
        if s == "Windows":
            return OSInfoLib._get_windows_osinfo()
        elif s == "Linux":
            return OSInfoLib._get_linux_osinfo()
        elif s == "Aix":
            return OSInfoLib._get_aix_osinfo()
        else:
            raise Exception("unknown system {!s} for the platform".format(s))

    @staticmethod
    def _get_linux_osinfo():
        """返回 Linux 主机系统信息
            {
                "platform": {
                    "os": "Linux",
                }
                "release": {
                    "distribute": "CentOS Linux",
                    "version": "7.6.1810",
                    "major": "7",
                },
            }
        """
        res = {"release": {}, "platform": {"os": "Linux"}}
        res["release"]["distribute"], res["release"]["version"] = platform.linux_distribution()[0:2]
        res["release"]["major"] = res["release"]["version"].split(".", 1)[0]

        return res

    @staticmethod
    def _get_windows_osinfo():
        riase Exception("unsupport windows now")

    @staticmethod
    def _get_aix_osinfo():
        raise Exception("unsupport aix now")
