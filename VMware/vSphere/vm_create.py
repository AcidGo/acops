#! /usr/local/pyenv/py-3.6.8-env-pyvmomi-6.7u3/bin/python3

# Author: AcidGo
# Usage:
#   pass
# Require:
#   Python 3.5+, not support Python 2.

import atexit
import logging
import re
import time
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect

# ########## CONFIG
# 创建虚拟机最大内存限制，单位为 GB
VM_MAX_MEM_GB = 20
# 创建虚拟机最大核数限制
VM_MAX_NUMCPU = 10
# 创建虚拟机最大每核限制
VM_MAX_PERSOCKET = 2
# 创建虚拟机磁盘容量总和限制，单位为 GB
VM_MAX_DISK_GB = 150
# 主机内存在此次操作后预估使用比值限制
HOST_MAX_MEM_PRO = 0.9
# 是否等待克隆任务完成，如果为 True 则一直挂住直至本次克隆失败或成功
IS_WAIT_CLONE = True
# 任务轮询间隔，仅在 IS_WAIT_CLONE 为 True 时有效
TASK_CHK_INTERVAL = 10
# 允许在间隔中连续出现 queued 的次数
TASK_QUEUED_TIMS = 3
# 在开机时等待操作系统运行的时间
WAIT_OS_RUN_SECOND = 30
# 第一次检查 IP 是否被占用时调用 ping 的次数
FIRST_PING_TIMES = 3
# 第二次检查 IP 是否正常使用时调用 ping 的次数
SECOND_PING_TIMES = 10
# 是否开启存储自主选择策略
IS_SMART_DATASTORE = True
# 如果开启存储自动选择，可用空间低于该值的存储将排除在外，单位为 GB
SMART_DATASTORE_MIN_FREE_GB = 100
# 对于 Linux 服务器，自定义配置中设置的默认主机名
CUSTOMIZE_LINUX_HOSTNAME = "baseline"
LOGGING_LEVEL = "DEBUG"
# 可用存储白名单
STORE_WHITE_LIST = [
]
# 可用存储黑名单
STORE_BLACK_LIST = [
    "datastore[0-9]+",
    "TMPVOL",
]
# 存储支持的文件系统
STORE_FS_SUPPORT = [
    "vmfs",
    "nas"
]
# VMware 中网络与真实网段的对应关系，该映射是为了针对某些不规范的网络命名而补充准备的
# 注意，如果从一个环境迁移至另一个环境，请务必确认此映射表正确
NET_MAPPING = {
}
# 是否倾向选择分布式虚拟交换机
NET_DVS_SKEW = True
# 映射常量
NET_DVS_TYPE = "_type_dvs"
NET_VSS_TYPE = "_type_vss"
# ########## EOF CONFIG

class VMCreate(VCConfig):
    def __init__(self):
        super(VMCreate, self).__init__()

    def set_params(self, **kwargs):
        # raw data for set_params
        self.settarget = kwargs["settarget"]
        self.setip = kwargs["setip"]
        self.setname = kwargs["setname"]
        self.setmem_gb = kwargs["setmem_gb"]
        self.setcpunum = kwargs["setcpunum"]
        self.setpersocket = kwargs["setpersocket"]
        self.sethostname = kwargs["sethostname"]
        self.ondatacenter = kwargs["ondatacenter"]
        self.oncluster = kwargs["oncluster"]
        self.onhost = kwargs["onhost"]
        self.ondatastore = kwargs["ondatastore"]
        self.onfolder = kwargs["onfolder"]
        self.setcomment = kwargs["setcomment"]

        self._params = {k: v for k, v in kwargs.items()}
        self._cuskey_tracing = {}
        self._cuskey_mapping = {}

        # validate params
        if not isinstance(self.setcomment, dict):
            raise Exception(f"the setcomment attr must be dict type, but it is {type(self.setcomment)}")

        # init for cook params
        self.mem_mb = None
        self.cpunum = None
        self.persocket = None
        self.datacenter = None
        self.cluster = None
        self.host = None
        self.datastore = None
        self.folder = None
        self.comment = {}

    def precheck(self):
        logging.info("the input args are:")
        for k, v in self._params.items():
            logging.info(f"\t{k}: {v}")

        service_instance = self.get_service_instance()
        tmp = VirtualMachineLib.get_vms_by_name(service_instance, self.settarget)

        # 可行性分析: 目标虚拟机对象是否可用
        if len(tmp) < 1:
            raise Exception(f"not found target virtual machine object by the search key: {self.settarget}")
        if len(tmp) != 1:
            raise Exception(f"found target many virtual machine objects, the nubmer is {len(tmp)}")
        self.target_vm = tmp[0]

        # 参数检查: 配置 IP 是否符合 IPv4 规范
        if self.setip and not re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", self.setip):
            raise Exception(f"the setip {self.setip} is invalid IPv4 format")

        # 可行性分析: 虚拟机名必须由 setname 或 setip 命令，因此两者不能全为空
        if not self.setip and not self.setname:
            raise Exception("both of setip and setname is null, cannot select name for new virtual machine")

        # 参数检查: 可使用 IP 作为虚拟机名
        if not self.setname:
            self.setname = self.setip

        # 可行性分析: IP 不可占用，且对支持自定义的系统提供 IP 配置
        if self.setip:
            if Utils.ping(self.setip):
                raise Exception(f"the ip {self.setip} had been used")

            cloning_os = ""
            if self.target_vm.guest.guestFullName:
                cloning_os = "windows" if "windows" in self.target_vm.guest.guestFullName.lower() else ""
            else:
                logging.warning("not found the guestFullName from the target virtual machine")
            # TODO: support for windows customize
            if cloning_os in ("windows", ):
                logging.warning("the cloning OS is windows, not support for the platform customize")
                self.setip = ""

        # 参数优化: 资源设置参数为整型
        self.mem_mb = int(self.setmem_gb)*1024 if self.setmem_gb else 0
        self.cpunum = int(self.setcpunum) if self.setcpunum else 0
        self.persocket = int(self.setpersocket) if self.setpersocket else 0

        # 参数优化: 资源设置参数如果为 0，则对齐目标虚拟机资源
        if self.mem_mb == 0:
            self.mem_mb = self.target_vm.config.hardware.memoryMB
        if self.cpunum == 0:
            self.cpunum = self.target_vm.config.hardware.numCPU
        if self.persocket == 0:
            self.persocket = self.target_vm.config.hardware.numCoresPerSocket

        # 资源分析: 新建的配置资源不能超过水位线
        if self.mem_mb/1024 > VM_MAX_MEM_GB:
            raise Exception(f"the memory for cloning vm is {self.mem_mb} MB, it is more than {VM_MAX_MEM_GB} GB")
        if self.cpunum > VM_MAX_NUMCPU:
            raise Exception(f"the cpunum for cloning vm is {self.cpunum}, it is more than {VM_MAX_NUMCPU}")
        if self.persocket > VM_MAX_PERSOCKET:
            raise Exception(f"the persocket for cloning vm is {self.persocket}, it is more than {VM_MAX_PERSOCKET}")

        # 资源分析: 克隆目标虚拟机的置备磁盘总和不允许超过水位线
        tmp = VirtualMachineLib.get_vm_disk_total_gb(self.target_vm)
        if tmp > VM_MAX_DISK_GB:
            raise Exception(f"the total disk cap for cloning vm is {tmp} GB, it is more than {VM_MAX_DISK_GB} GB")

        if not self.onhost:
            # 可行性分析: 没有直接指定主机时，必须指定的最低粒度为集群
            if not self.ondatacenter and not self.oncluster:
                raise Exception("not active way for found host or cluster for cloning virtual machine")
            # 没有定义主机而仅有集群时，可预测是否只有一个数据中心满足使用
            elif self.oncluster:
                tmp = DatacenterLib.list_datacenters(service_instance)
                if len(tmp) == 0:
                    raise Exception("not found datacenter, but we need it")
                elif len(tmp) == 1:
                    # 可行性分析: 指定的数据中心与仅有的一个名称不一致
                    if self.ondatacenter and tmp[0].name != self.ondatacenter:
                        raise Exception(f"found only one datacenter {tmp[0].name}, but you had select {self.ondatacenter}")
                    self.datacenter = tmp[0]
                    logging.info(f"through cluster name, found a datacenter for cloning virtual machine: {self.datacenter.name}")

                    # 在该数据中心下检索集群
                    tmp = ClusterLib.get_clusters_on_datacenter_by_name(self.datacenter, self.oncluster)
                    if len(tmp) == 0:
                        raise Exception(f"not found cluster from {self.datacenter.name}")
                    elif len(tmp) != 1:
                        for i in tmp:
                            logging.info(f"")
                        raise Exception(f"found {len(tmp)} clusters from {self.datacenter.name} by name {self.oncluster}")
                    else:
                        self.cluster = tmp[0]
                else:
                    for i in tmp:
                        if self.ondatacenter and i.name == self.ondatacenter:
                            self.datacenter = i
                            cluster_list = ClusterLib.get_clusters_on_datacenter_by_name(self.datacenter, self.oncluster)
                            self.cluster = cluster_list[0] if len(cluster_list) > 0 else None
                            break
                        if not self.ondatacenter:
                            cluster_list = ClusterLib.get_clusters_on_datacenter_by_name(i, self.oncluster)
                            if len(cluster_list) == 0:
                                continue
                            self.cluster = cluster_list[0]
                            self.datacenter = i
                            logging.info(f"choosing datacenter {self.datacenter.name} and cluster {self.cluster.name} for using")
                            break
                    else:
                        raise Exception("no through host for selecting, and datacenters selected is more than one")
            else:
                # TODO: 不排除一些特殊环境将主机放置于数据中心
                raise Exception("both onhost and oncluster is null")
        else:
            tmp = HostLib.get_hosts_by_name(service_instance, self.onhost)
            if len(tmp) < 1:
                raise Exception(f"not found target host object by the search key: {self.onhost}")
            if len(tmp) != 1:
                raise Exception(f"found target many host objects, the nubmer is {len(tmp)}")

            self.host = tmp[0]

            if self.oncluster:
                tmp = VBaseLib.find_parent_resource(self.host, vim.ClusterComputeResource)
                if tmp is not None and self.oncluster != tmp.name:
                    raise Exception(f"through the host, it's cluster {tmp.name} is not equal oncluster {self.oncluster}")

            if self.ondatacenter:
                tmp = VBaseLib.find_parent_resource(self.host, vim.Datacenter)
                if tmp is not None and self.ondatacenter != tmp.name:
                    raise Exception(f"through the host, it's cluster {tmp.name} is not equal oncluster {self.ondatacenter}")

        # 参数优化: 如果只存在目标集群可定位，则选择最适合的主机来使用
        if not self.host and self.cluster:
            tmp = ClusterLib.pick_host_with_resource(self.cluster)
            if tmp is None:
                raise Exception("pick host from cluster is failed")
            else:
                self.host = tmp
                logging.debug(f"pick a host from cluster: {self.host.name}")

        if not self.cluster:
            self.cluster = ClusterLib.get_cluster_by_host(self.host)
            if not self.cluster:
                raise Exception(f"cannot get cluster by host {self.host.name}")

        # 可行性分析: 目标主机必须可用，不能为空实例、维护模式、离线状态等
        if not VBaseLib.is_host(self.host):
            raise Exception("the host found is not host type")
        else:
            # TODO: add another state, such as no-accessiable ...
            if HostLib.in_maintenance_mode(self.host):
                raise Exception(f"the host {self.host.name} is inMaintenanceMode, cannot be used")

        # 参数优化: 定位集群
        host_datacenter = DatacenterLib.get_datacenter_by_host(self.host)
        if not self.datacenter:
            self.datacenter = host_datacenter
        elif self.datacenter.name != host_datacenter.name:
            raise Exception(f"datacenter {host_datacenter.name} searched by host {self.host.name}, but abover datacenter found is {self.datacenter.name}")

        # 参数优化: 检查目录
        if self.onfolder and not self.datacenter:
            raise Exception(f"not found datacenter by host {self.host.name} for folder")
        if self.onfolder:
            # TODO: support recurse folders
            for e in self.datacenter.vmFolder.childEntity:
                if self.onfolder == e.name:
                    self.folder = e
                    break
            else:
                raise Exception(f"not found the folder on datacenter: {self.onfolder}")
        else:
            self.folder = self.datacenter.vmFolder

        # 资源分析: 主机加上新建虚拟机总内存后的空闲内存不能低于限制的百分比
        host_memusage_gauge = float(self.host.summary.quickStats.overallMemoryUsage + self.target_vm.config.hardware.memoryMB)/(self.host.hardware.memorySize/(1024**2))
        if host_memusage_gauge > HOST_MAX_MEM_PRO:
            raise Exception(f"host memusage gauge is {host_memusage_gauge}, more than {HOST_MAX_MEM_PRO}")

        # 参数检查: 用以对新建虚拟机的命名的参数必须保证不能冲突重复
        if self.setname:
            tmp = VirtualMachineLib.get_vms_by_name(service_instance, self.setname)
            if len(tmp) > 0:
                raise Exception(f"another named {self.setname} is exsits")

        # 可行性分析: 选中存储必须在指定主机内
        if self.ondatastore:
            for ds in self.host.datastore:
                if ds.name == self.ondatastore:
                    self.datastore = ds
                    break
            else:
                raise Exception(f"not found the datastore on host {self.host.name} by {self.ondatastore}")
        # 使用存储自主选择
        elif IS_SMART_DATASTORE is True:
            logging.debug("changing to smart choosing datastore ......")
            # 文件系统仅考虑允许格式
            # 存储必须多路径
            # 可用空间需大于水位线
            ds_list = [ds for ds in self.host.datastore if DatastoreLib.has_support_fs(ds, STORE_FS_SUPPORT) and ds.summary.multipleHostAccess is True and ds.summary.freeSpace > SMART_DATASTORE_MIN_FREE_GB*1024*1024*1024]

            # 根据存储黑名单做过滤
            if STORE_BLACK_LIST:
                ds_pop_list = []
                for ds in ds_list:
                    for i in STORE_BLACK_LIST:
                        if re.search(i, ds.name):
                            ds_pop_list.append(ds)
                ds_list = [ds for ds in ds_list if ds not in ds_pop_list]

            # 根据存储白名单做过滤
            if STORE_WHITE_LIST:
                ds_only_list = []
                for ds in ds_list:
                    for i in STORE_WHITE_LIST:
                        if re.search(i, ds.name):
                            ds_only_list.append(ds)
                ds_list = [ds for ds in ds_only_list]

            if not ds_list:
                raise Exception("no datastore can be selected")

            # 根据可用空间大小排序
            ds_list.sort(key=lambda x: x.summary.freeSpace, reverse=True)
            self.datastore = ds_list[0]
            logging.debug(f"after smart choosing datastore, found the datastore: {self.datastore.name}")
        else:
            raise Exception(f"the ondatastore {self.ondatastore} is invalid")

        # 填充自定义字段追踪
        self._cuskey_tracing = VBaseLib.get_cuskey_tracing(service_instance)
        self._cuskey_mapping = {v: k for k, v in self._cuskey_tracing.items()}
        # 检查备注和自定义字段传入
        setcomment = {}
        for k, v in self.setcomment.items():
            if k == 0:
                setcomment[k] = v
                continue
            if k not in self._cuskey_tracing:
                logging.warning(f"the input name of custom field {k} not in the vCenter, ignore it")
                continue
            elif not v:
                logging.warning(f"the input name of custom field {k} is empty, ignore it")
                continue
            else:
                setcomment[self._cuskey_tracing[k]] = v
        self.setcomment = setcomment

    def execute(self):
        logging.info("after pre-check, optimized args are:")
        logging.info(f"\tsetip: {self.setip}")
        logging.info(f"\tsetname: {self.setname}")
        logging.info(f"\tmem_mb: {self.mem_mb}")
        logging.info(f"\tcpunum: {self.cpunum}")
        logging.info(f"\tpersocket: {self.persocket}")
        logging.info(f"\tsethostname: {self.sethostname}")
        if self.datacenter:
            logging.info(f"\tdatacenter: {self.datacenter.name}")
        else:
            logging.info("\tdatacenter: None")
        if self.cluster:
            logging.info(f"\tcluster: {self.cluster.name}")
        else:
            logging.info("\tcluster: None")
        if self.host:
            logging.info(f"\thost: {self.host.name}")
        else:
            logging.info("\thost: None")
        if self.datastore:
            logging.info(f"\tdatastore: {self.datastore.name}")
        else:
            logging.info("\tdatastore: None")
        if self.folder:
            logging.info(f"\tfolder: {self.folder.name}")
        else:
            logging.info("\tfolder: None")
        logging.info(f"\tsetcomment: {self.setcomment}")

        service_instance = self.get_service_instance()
        # 新建虚拟机资源定义
        relocate_spec = vim.vm.RelocateSpec()
        relocate_spec.datastore = self.datastore
        relocate_spec.host = self.host
        # TODO: select all resource pool in cluster
        relocate_spec.pool = self.cluster.resourcePool

        # 新建虚拟机属性配置
        vmconf_spec = vim.vm.ConfigSpec()
        if self.cpunum:
            vmconf_spec.numCPUs = self.cpunum
        if self.persocket:
            vmconf_spec.numCoresPerSocket = self.persocket
        if self.mem_mb:
            vmconf_spec.memoryMB = self.mem_mb
        # 默认启用 CPU 热插拔与内存热插拔
        vmconf_spec.cpuHotAddEnabled = True
        vmconf_spec.memoryHotAddEnabled = True

        # 更改的设备集合
        devices_change = []
        # 适配器集合
        adaptermaps = []

        # 自定义命名空间，此处仅当设置了 IP 配置才生效
        custom_spec = None
        if self.setip:
            self.setip, subnet_mask, ip_gateway = Utils.gen_ip_baseline(self.setip)

            guest_map = vim.vm.customization.AdapterMapping()
            guest_map.adapter = vim.vm.customization.IPSettings()
            guest_map.adapter.ip = vim.vm.customization.FixedIp()
            guest_map.adapter.ip.ipAddress = self.setip
            guest_map.adapter.subnetMask = subnet_mask
            guest_map.adapter.gateway = ip_gateway
            logging.info(f"on customization, the gateway is {ip_gateway}")
            adaptermaps.append(guest_map)

            # TODO: split multi OS
            ident = vim.vm.customization.LinuxPrep()
            ident.hostName = vim.vm.customization.FixedName()

            # 自定义配置的主机名
            if not self.sethostname:
                set_hostname = CUSTOMIZE_LINUX_HOSTNAME
            else:
                set_hostname = self.sethostname
            ident.hostName.name = set_hostname
            globalip = vim.vm.customization.GlobalIPSettings()

            custom_spec = vim.vm.customization.Specification()

            if len(adaptermaps) > 0:
                custom_spec.nicSettingMap = adaptermaps
            else:
                # 如果目标虚拟机没有网卡，则无法进行 IP 配置
                raise Exception("you set the ip, but the target has zero networkcard, not customize")

            custom_spec.identity = ident
            custom_spec.globalIPSettings = globalip

            # 选择网络映射标签
            net_format, net_tag = Utils.select_net_from_mapping(self.setip, NET_MAPPING)
            logging.debug(f"select the net format is {net_format} and net tag is {net_tag} on host {self.host.name}")
            target_network = None
            if NET_DVS_SKEW:
                dvs_pgs = []
                if net_format:
                    dvs_pgs = NetworkLib.get_dvs_networks_on_host(self.host, net_format)
                if not dvs_pgs:
                    if net_tag:
                        dvs_pgs = NetworkLib.get_dvs_networks_on_host(self.host, net_tag)
                if dvs_pgs:
                    target_network = NetworkLib.select_portgroup_on_host(dvs_pgs, self.host)
            if not target_network:
                vss_pgs = []
                if net_format:
                    vss_pgs = NetworkLib.get_vss_portgroups_by_name(service_instance, net_format)
                if not vss_pgs:
                    if net_tag:
                        vss_pgs = NetworkLib.get_vss_portgroups_by_name(service_instance, net_tag)
                if vss_pgs:
                    target_network = NetworkLib.select_portgroup_on_host(vss_pgs, self.host)
            if not target_network:
                raise Exception(f"cannot select one target network by {net_format} or {net_tag} on host {self.host.name}")

            target_network_type = NET_DVS_TYPE if isinstance(target_network, vim.dvs.DistributedVirtualPortgroup) else NET_VSS_TYPE
            target_network_name = target_network.name
            logging.info(f"after find network with {net_format} or {net_tag}, get [{target_network_type}](type) port group: {target_network_name}")

            nic_spec = vim.vm.device.VirtualDeviceSpec()
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            for dev in self.target_vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                    break
            else:
                raise Exception("cannot found the VirtualEthernetCard on the target")

            if not isinstance(target_network, vim.dvs.DistributedVirtualPortgroup):
                nic_spec.device = dev
                # 开启该网卡设备的打开电源时连接
                nic_spec.device.wakeOnLanEnabled = True
                nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                nic_spec.device.connectable.allowGuestControl = True
                nic_spec.device.connectable.startConnected = True
                # 测试了无法在克隆配置里一次性完成网卡启动连接配置，与官方开发者沟通，目前(pyVmomi 6.0)是无法实现
                # nic_spec.device.connectable.connected = False
                # nic_spec.device.connectable.status = "untried"

                # 选择网络连接的标签
                nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nic_spec.device.backing.network = target_network
                nic_spec.device.backing.deviceName = target_network.name
            else:
                dvs = target_network.config.distributedVirtualSwitch
                portKey = NetworkLib.search_dvs_port(dvs, target_network.key)
                port = NetworkLib.find_dvs_port(dvs, portKey)

                nic_spec.device = dev
                # 开启该网卡设备的打开电源时连接
                nic_spec.device.wakeOnLanEnabled = True

                nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                nic_spec.device.connectable.allowGuestControl = True
                nic_spec.device.connectable.startConnected = True

                nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nic_spec.device.backing.port = vim.dvs.PortConnection()
                nic_spec.device.backing.port.portgroupKey = port.portgroupKey
                nic_spec.device.backing.port.switchUuid = port.dvsUuid
                nic_spec.device.backing.port.portKey = port.key

            devices_change.append(nic_spec)

        if len(devices_change) > 0:
            vmconf_spec.deviceChange = devices_change

        clone_spec = vim.vm.CloneSpec()

        # 新建的虚拟机初始为关机状态
        clone_spec.powerOn = False
        clone_spec.location = relocate_spec
        clone_spec.config = vmconf_spec

        if custom_spec:
            clone_spec.customization = custom_spec

        logging.info("begin running clone task")
        task = self.target_vm.Clone(folder=self.folder, name=self.setname, spec=clone_spec)
        if IS_WAIT_CLONE:
            if not VBaseLib.wait_for_task(task, TASK_CHK_INTERVAL):
                raise Exception("waiting the task is error")
        else:
            logging.info("done, not wait for clone task and no post-check")
            return 

        # 检查新建的虚拟机是否符合预期
        logging.info("begin checking the new vm")
        # hardcore: 为了等待 VC 刷新新加的虚拟机信息
        time.sleep(5)
        tmp = VirtualMachineLib.get_vms_by_name(self.get_service_instance(), self.setname)
        if not tmp:
            raise Exception("not found the cloned virtual machine")
        if len(tmp) > 1:
            raise Exception("found the cloned virtual machine is multi")
        self.cloned_vm = tmp[0]

        try:
            logging.info(f"setting annotation: old:[{self.cloned_vm.config.annotation}] -> new:[{self.setcomment[0]}]")
            VirtualMachineLib.set_vm_annotation(self.cloned_vm, self.setcomment[0])
        except Exception as e:
            logging.error("faild to set annotation")
            logging.exception(e)
        logging.info("done set annotation")

        # 自定义栏
        custom_mgr = self.get_service_instance().RetrieveContent().customFieldsManager
        old_custom_lst = {i.key: i.value for i in self.cloned_vm.customValue}

        for field_key, field_val in self.setcomment.items():
            if field_key == 0:
                continue
            logging.info(f"Start set custom-key:[{self._cuskey_mapping[field_key]}]: old:[{old_custom_lst.get(field_key, 'NULL')}] -> new:[{field_val}]")

            try:
                custom_mgr.SetField(entity=self.cloned_vm, key=field_key, value=str(field_val))
            except Exception as e:
                logging.warning(f"faild to set custom, key: {self._cuskey_mapping[field_key]}")

        logging.info("done set custom")

        # 检查新建虚拟机所在主机是否符合预期
        if self.cloned_vm.runtime.host != self.host:
            raise Exception("the cloned vm's host is not expected")
        # 检查新建虚拟机的 CPU 槽数是否符合预期
        if self.cloned_vm.config.hardware.numCPU != self.cpunum:
            logging.error("The new vm's numCPU is not good.")
            raise Exception("")

        # 开机，并进行网络测试，以确保 IP 正确
        if self.setip:
            # 1. 先检查 IP 是否不被占用，连续检查三次，避免 arp 延迟
            logging.info(f"start ping-check the setip:[{self.setip}]")
            ipused = False
            for i in range(FIRST_PING_TIMES):
                if Utils.ping(self.setip) is True:
                    ipused = True
                    break
            if ipused is True:
                raise Exception("the setip:[{self.setip}] is used, it is found by ping-check")
            else:
                logging.info(f"the setip:[{self.setip}] is not used, ipused is [{ipused}]")

            # 2. 保持网卡断开后开启虚拟机
            # 2.1 判断当前是否为关机状态
            if self.cloned_vm.runtime.powerState != vim.VirtualMachine.PowerState.poweredOff:
                raise Exception("the new vm is not poweroff, stop to poweron and ping-check")

            # 2.2 保证所有网卡的自启动连接都是关闭
            for dev in self.cloned_vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                    if dev.connectable.startConnected:
                        logging.info(f"the networkcard:[{dev.deviceInfo.label}] is startconnected, disable it")
                        VirtualMachineLib.change_net_startconnected(self.cloned_vm, dev, False)
            # 配置更改后再次查看，不允许有自启动连接是开启的
            for dev in self.cloned_vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                    if dev.connectable.startConnected:
                        raise Exception(f"the networkcard:[{dev.deviceInfo.label}] is still startconnected")

            # 2.3 打开虚拟机
            logging.info("poweron the new vm")
            task = self.cloned_vm.PowerOn()
            logging.info(f"waitting {WAIT_OS_RUN_SECOND} second")
            time.sleep(WAIT_OS_RUN_SECOND)
            if self.cloned_vm.runtime.powerState != vim.VirtualMachine.PowerState.poweredOn:
                raise Exception("the new vm is not poweroned")

            # 3. 打开虚拟机网卡连接和自连接
            # 注：当前仅仅支持全部网卡统一操作
            for dev in self.cloned_vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualEthernetCard):
                    if not dev.connectable.startConnected or not dev.connectable.connected:
                        logging.info("enable the startConnected and connected")
                        VirtualMachineLib.enable_net_connect(self.cloned_vm, dev)

            # 4. 等待一定时间后进行 ping 测试，判断是否 IP 正确
            time.sleep(10)
            logging.info("start second ping-check")
            ipused_second = False
            for i in range(SECOND_PING_TIMES):
                if Utils.ping(self.setip) is True:
                    ipused_second = True
                    break
            if ipused is False and ipused_second is True:
                logging.info("the new vm ip setting and checking is successful. All works is done. FINISH ......")
            else:
                raise Exception(f"the second ping-check is not found ipused. Please check. ipused: {ipused} , ipused_second: {ipused_second}")

        else:
            logging.info("setip is empty, not check ip and poweron it")

        logging.info("the new vm check is ok")

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

    logging.info("Logger init finished.")

def execute(vc_connect_args, vm_create_args):
    vm_create = VMCreate()
    vm_create.config(**vc_connect_args)
    vm_create.get_service_instance()
    vm_create.set_params(**vm_create_args)

    logging.info("start pre-check task ......")
    vm_create.precheck()
    logging.info("finish pre-check")

    vm_create.execute()
    
    logging.info("start post-check task ......")
    vm_create.postcheck()
    logging.info("finish post-check")

if __name__ == "__main__":
    # ########## Self Test
    # ########## EOF Self Test

    init_logger(LOGGING_LEVEL)

    vc_connect_args = {
        "host": INPUT_VC_HOST,
        "user": INPUT_VC_USER,
        "password": INPUT_VC_PASSWORD,
        "has_ssl": False,
    }

    vm_create_args = {
        "settarget": INPUT_TARGET,
        "setip": INPUT_SETIP,
        "setname": INPUT_SETNAME,
        "setmem_gb": INPUT_SETMEM,
        "setcpunum": INPUT_SETCPUNUM,
        "setpersocket": INPUT_SETPERSOCKET,
        "sethostname": None,
        "ondatacenter": INPUT_ONDATACENTER,
        "oncluster": INPUT_ONCLUSTER,
        "onhost": INPUT_ONHOST,
        "ondatastore": INPUT_DATASTORE,
        "onfolder": INPUT_ONFOLDER,
        "setcomment": {
            "应用名称": INPUT_COMMENT_FILED_1,
            "应用系统": INPUT_COMMENT_FILED_2,
            "负责人":   INPUT_COMMENT_FILED_3,
            0: INPUT_ANNOTATION,
        },
    }

    execute(vc_connect_args, vm_create_args)