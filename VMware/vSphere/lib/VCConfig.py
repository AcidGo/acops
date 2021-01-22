from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect

class VCConfig(object):
    """vCenter 配置类，由其配置执行的配置参数。
    """

    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 443
        self.user = ""
        self.password = ""
        self.has_ssl = False
        self._service_instance = None

    def config(self, **kwargs):
        """配置 vCenter 连接参数和使用配置。
        """
        self.host = kwargs["host"]
        self.port = kwargs.get("port", 443)
        self.user = kwargs["user"]
        self.password = kwargs["password"]
        self.has_ssl = kwargs["has_ssl"]

    def get_service_instance(self):
        """获取可用的 vCenter 连接。
        """
        if self._checkalive_service_instance():
            return self._service_instance
        elif self._service_instance is not None:
            # TODO: 可以更加人性化地断开并取消 atexit 注册的关闭回调
            Disconnect(self._service_instance)

        connect = SmartConnect if self.has_ssl is True else SmartConnectNoSSL
        try:
            service_instance = connect(
                host    = self.host,
                user    = self.user,
                pwd     = self.password,
                port    = self.port,
            )
        # 对于其他错误直接报错
        except vim.fault.InvalidLogin as e:
            raise Exception(e.msg)

        self._service_instance = service_instance
        # 注册退出前的主动断开回调
        atexit.register(Disconnect, self._service_instance)

        return self._service_instance

    def _checkalive_service_instance(self):
        """检查当前持有的服务连接是否可用。
        """
        # TODO: 更加完善的检测机制
        if self._service_instance:
            return True
        else:
            return False