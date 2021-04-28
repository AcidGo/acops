class Utils(object):
    @staticmethod
    def ping(host):
        """通过调用操作系统的 ping 工具做 ICMP 测试。
        """
        import subprocess, platform
        ping_str = "-n 1 -w 3000" if platform.system().lower() == "windows" else "-c 1"
        args = "ping {!s} {!s}".format(ping_str, host)
        need_sh = False if platform.system().lower() == "windows" else True
        return subprocess.call(args, shell=need_sh, stdout=subprocess.DEVNULL) == 0

    @staticmethod
    def gen_ip_baseline(ip):
        """根据网络基线分配子网和网关。
        """
        subnet_mask = "255.255.255.0"
        gateway = ".".join([j for i,j in enumerate(ip.split('.')) if i != 3]) + ".254"
        return ip, subnet_mask, gateway

    @staticmethod
    def select_net_from_mapping(ip, mapping):
        """根据 IP 信息从端口组的网络映射表获取端口组标签。
        """
        f = ".".join([j for i, j in enumerate(ip.split(".")) if i != 3]) + ".x"
        t = None
        for k, v in mapping.items():
            if v == f:
                t = k
        return f, t