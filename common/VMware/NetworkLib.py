class NetworkLib(object):
    @staticmethod
    def get_vss_portgroups_by_name(service_instance, name):
        """
        """
        pgs = []
        networks = VBaseLib.get_objects_by_name(service_instance, name, vim.Network)
        for net in networks:
            if not isinstance(net, vim.Network):
                logging.warning(f"the object expected vim.Network is {type(net)}")
                continue
            if isinstance(net, vim.dvs.DistributedVirtualPortgroup):
                continue
            pgs.append(net)

    @staticmethod
    def get_dvs_portgroups_by_name(service_instance, name):
        return  VBaseLib.get_objects_by_name(service_instance, name, vim.dvs.DistributedVirtualPortgroup)

    @staticmethod
    def get_dvs_networks_on_host(host, name):
        pgs = []
        for i in host.network:
            if i.name == name and isinstance(i, vim.dvs.DistributedVirtualPortgroup):
                pgs.append(i)
        return pgs

    @staticmethod
    def search_dvs_port(dvs, portgroupkey):
        """
        """
        search_portkey = []
        criteria = vim.dvs.PortCriteria()
        criteria.connected = False
        criteria.inside = True
        criteria.portgroupKey = portgroupkey
        ports = dvs.FetchDVPorts(criteria)

        for port in ports:
            search_portkey.append(port.key)
        return search_portkey[0]

    @staticmethod
    def find_dvs_port(dvs, key):
        """
        """
        obj = None
        ports = dvs.FetchDVPorts()
        for c in ports:
            if c.key == key:
                obj = c
        return obj

    @staticmethod
    def select_portgroup_on_host(pgs, host):
        for pg in pgs:
            for net in host.network:
                if pg.name == net.name:
                    return pg
        return None