class ClusterLib(object):
    @staticmethod
    def get_clusters_by_name(service_instance, name):
        return VBaseLib.get_objects_by_name(service_instance, name, vim.ClusterComputeResource)

    @staticmethod
    def get_cluster_by_host(host):
        return VBaseLib.find_parent_resource(host, vim.ClusterComputeResource)

    @staticmethod
    def get_clusters_on_datacenter_by_name(datacenter, name):
        _max_recursion_depth = 2
        objs = []

        if not isinstance(datacenter, vim.Datacenter):
            return objs

        for e in datacenter.hostFolder.childEntity:
            VBaseLib.find_child_entities(e, vim.ClusterComputeResource, _max_recursion_depth, objs)

        objs = [obj for obj in objs if obj.name == name]

        return objs

    @staticmethod
    def list_hosts(cluster, no_maintenance_mode):
        hosts = []
        for h in cluster.host:
            if no_maintenance_mode and HostLib.in_maintenance_mode(h):
                continue
            hosts.append(h)
        return hosts

    @staticmethod
    def pick_host_with_resource(cluster):
        """根据一定的算法策略，从目标集群中挑选合适的主机。
        """
        hosts = ClusterLib.list_hosts(cluster, no_maintenance_mode=True)
        if len(hosts) < 1:
            return None
        mem_weights  = sorted(hosts, key=lambda x: x.summary.quickStats.overallCpuUsage)
        cpu_weights  = sorted(hosts, key=lambda x: x.summary.quickStats.overallMemoryUsage)
        host_weights = sorted(hosts, key=lambda x: mem_weights.index(x) + cpu_weights.index(x))
        return host_weights[0]