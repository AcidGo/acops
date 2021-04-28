# acops

一些自己编写的，在工作中使用体验比较良好的自动化工具，可开源部分。

### VMware/vm_create

智能创建 VMware vSphere vCenter/ESXi 虚拟机，可根据网络设置自动探测并分配 IP 资源，可对集群主机、存储、虚拟交换机端口组（含分布式交换机）等做调度分配。

### FS/NFS/nfs-dig

检查 nfs 共享文件系统挂载情况，并对远程提供服务主机做 RPC 端口和 NFS PortMap 对应端口做探测，报告结果。