class DatacenterLib(object):
    @staticmethod
    def get_datacenters_by_name(service_instance, name):
        return VBaseLib.get_objects_by_name(service_instance, name, vim.Datacenter)

    @staticmethod
    def get_datacenters_by_cluster(cluster):
        return VBaseLib.find_parent_resource(cluster, vim.ClusterComputeResource)

    @staticmethod
    def list_datacenters(service_instance):
        return VBaseLib.get_objects_by_type(service_instance, vim.Datacenter)

    @staticmethod
    def get_datacenter_by_host(host):
        return VBaseLib.find_parent_resource(host, vim.Datacenter)