class HostLib(object):
    @staticmethod
    def get_hosts_by_name(service_instance, name):
        """
        """
        return VBaseLib.get_objects_by_name(service_instance, name, vim.HostSystem)

    @staticmethod
    def list_portgroups(host):
        return host.network

    @staticmethod
    def in_maintenance_mode(host):
        if hasattr(host.runtime, "inMaintenanceMode") and host.runtime.inMaintenanceMode:
            return True
        return False