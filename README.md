# acops

一些自己编写的，在工作中使用体验比较良好的自动化工具，可开源部分。

### VMware/vm_create

智能创建 VMware vSphere vCenter/ESXi 虚拟机，可根据网络设置自动探测并分配 IP 资源，可对集群主机、存储、虚拟交换机端口组（含分布式交换机）等做调度分配。

+ 配置项目

  | 配置项                      | 说明                                                         |
  | --------------------------- | ------------------------------------------------------------ |
  | VM_MAX_MEM_GB               | 创建虚拟机最大内存限制，单位为 GB。                          |
  | VM_MAX_NUMCPU               | 创建虚拟机最大核数限制。                                     |
  | VM_MAX_PERSOCKET            | 创建虚拟机最大每核限制。                                     |
  | VM_MAX_DISK_GB              | 创建虚拟机磁盘容量总和限制，单位为 GB。                      |
  | HOST_MAX_MEM_PRO            | 主机内存在此次操作后预估使用比值限制。                       |
  | IS_WAIT_CLONE               | 是否等待克隆任务完成，如果为 True 则一直挂住直至本次克隆失败或成功。 |
  | TASK_CHK_INTERVAL           | 务轮询间隔，仅在 IS_WAIT_CLONE 为 True 时有效。              |
  | TASK_QUEUED_TIMS            | 允许在间隔中连续出现 queued 的次数                           |
  | WAIT_OS_RUN_SECOND          | 在开机时等待操作系统运行的时间。                             |
  | FIRST_PING_TIMES            | 第一次检查 IP 是否被占用时调用 ping 的次数。                 |
  | SECOND_PING_TIMES           | 第二次检查 IP 是否正常使用时调用 ping 的次数。               |
  | IS_SMART_DATASTORE          | 是否开启存储自主选择策略。                                   |
  | SMART_DATASTORE_MIN_FREE_GB | 如果开启存储自动选择，可用空间低于该值的存储将排除在外，单位为 GB。 |
  | CUSTOMIZE_LINUX_HOSTNAME    | 对于 Linux 服务器，自定义配置中设置的默认主机名。            |
  | LOGGING_LEVEL               | 执行日志级别。                                               |
  | STORE_WHITE_LIST            | 可用存储白名单。                                             |
  | STORE_BLACK_LIST            | 可用存储黑名单。                                             |
  | STORE_FS_SUPPORT            | 存储支持的文件系统。                                         |
  | NET_MAPPING                 | VMware 中网络与真实网段的对应关系，该映射是为了针对某些不规范的网络命名而补充准备的。 |
  | NET_DVS_SKEW                | 是否倾向选择分布式虚拟交换机。                               |

+ 执行参数

  | 参数         | 说明                                                         |
  | ------------ | ------------------------------------------------------------ |
  | settarget    | 用于克隆的虚机或模板名称，必填。                             |
  | setip        | 设置新建虚机默认网关网卡的 IP 地址。                         |
  | setname      | 设置新建虚机名称，为空时优先使用 IP 填充。                   |
  | setmem_gb    | 分配虚机内存大小，单位为 GB，为空则与目标对象一致。          |
  | setcpunum    | 分配虚机 CPU 物理核插槽数，为空则与目标对象一致。            |
  | setpersocket | 分配虚机 CPU 每插槽物理核数，为空则与目标对象一致。          |
  | sethostname  | 配置虚机操作系统主机名。                                     |
  | ondatacenter | 选定部署虚机的数据中心，为空则自动选择 ESXi 主机所在数据中心或唯一数据中心。 |
  | oncluster    | 选定部署虚机的集群，为空则自动选择 ESXi 主机所在集群的 resourcePool。 |
  | onhost       | 选定部署虚机的 ESXi 主机，为空则自动选择集群内负载最低的主机。 |
  | ondatastore  | 选定部署虚机的存储卷，为空则根据黑白名单选择可用存储中可用容量最高的 LUN。 |
  | onfolder     | 选定放置虚机的文件目录，为空则放于默认 vm 目录。             |
  | setcomment   | 配置虚机自定义栏和备注，可以根据实际内容自行调配，0 为备注信息。 |

  