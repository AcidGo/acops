class VirtualMachineLib(object):
    @staticmethod
    def get_vms_by_name(service_instance, name):
        """
        """
        return VBaseLib.get_objects_by_name(service_instance, name, vim.VirtualMachine)

    @staticmethod
    def get_vm_disk_total_gb(vm):
        total_kb = 0
        for d in vm.config.hardware.device:
            if isinstance(d, vim.vm.device.VirtualDisk):
                total_kb += d.capacityInKB
        return total_kb/(1024**2)

    @staticmethod
    def set_vm_annotation(vm, msg):
        """
        """
        if not msg:
            return 
        msg = str(msg)
        vmconf_spec = vim.vm.ConfigSpec(annotation=msg)
        task = vm.Reconfigure(vmconf_spec)
        if not VBaseLib.wait_for_task(task, TASK_CHK_INTERVAL):
            raise Exception("waitting task of set annotation is error")

    @staticmethod
    def change_net_startconnected(vm, ethcard_obj, isconnected):
        """调整虚拟机的指定网卡的打开电源时连接。

        Args:
            vm: 操作的虚拟机对象实例。
            ethcard_obj: 操作的网卡的对象。
            isconnected: 是否开启。
        """
        devices_change = []
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_spec.device = ethcard_obj
        nic_spec.device.connectable.startConnected = isconnected
        devices_change.append(nic_spec)

        vmconf_spec = vim.vm.ConfigSpec()
        vmconf_spec.deviceChange = devices_change
        task = vm.ReconfigVM_Task(vmconf_spec)
        if not VBaseLib.wait_for_task(task, TASK_CHK_INTERVAL):
            raise Exception("waitting task of change network card startConnected is error")

    @staticmethod
    def enable_net_connect(vm, ethcard_obj):
        """将执行虚拟机的网卡对象配置连接和开机自动连接。

        Args:
            vm: 操作的虚拟机对象实例。
            ethcard_obj: 操作的网卡的对象。
        """
        devices_change = []
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_spec.device = ethcard_obj
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.connected = True

        vmconf_spec = vim.vm.ConfigSpec()
        vmconf_spec.deviceChange = devices_change
        task = vm.ReconfigVM_Task(vmconf_spec)
        if not VBaseLib.wait_for_task(task, TASK_CHK_INTERVAL):
            raise Exception("waitting task of enable network card startConnected is error")