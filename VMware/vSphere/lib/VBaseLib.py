import logging
import re
import time
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect

class VBaseLib(object):
    @staticmethod
    def get_object_by_name(service_instance, name, type_):
        """
        """
        objs = VBaseLib.get_objects_by_name(service_instance, name, type_, onely_one=True)
        return objs[0] if len(objs) > 0 else None

    @staticmethod
    def get_objects_by_name(service_instance, name, type_, onely_one=False):
        """
        """
        objs = []
        if not isinstance(name, (str,)) or name == '':
            raise Exception(f"the name of target is invalid, type is {type(name)}, value is {name}")
        content = service_instance.RetrieveContent()
        container = content.viewManager.CreateContainerView(content.rootFolder, [type_], True)
        for c in container.view:
            try:
                if c.name == name:
                    objs.append(c)
                    if onely_one:
                        break
            except vmodl.fault.ManagedObjectNotFound as e:
                logging.debug(f"a not found managed object, ignore it")
                # hardcore: waitting some seconds for cleanup resources jobs
                time.sleep(10)
                continue
        # 销毁视图，回收资源
        container.Destroy()
        return objs

    @staticmethod
    def get_objects_by_type(service_instance, type_):
        objs = []
        content = service_instance.RetrieveContent()
        container = content.viewManager.CreateContainerView(content.rootFolder, [type_], True)
        for c in container.view:
            objs.append(c)
        # 销毁视图，回收资源
        container.Destroy()
        return objs

    @staticmethod
    def select_portgroup_by_host(pgs, host, dvs_skew):
        """
        """
        vss_list = []
        dvs_list = []
        host_pgs = HostLib.list_portgroups()
        for pg in pgs:
            # 跳过不可达的失效网络
            if not pg.summary.summary.accessible:
                continue
            # 端口组需要与给定主机关联
            if not NetworkLib.portgroup_in_list(pg, host_pgs):
                continue
            if isinstance(pg, vim.dvs.DistributedVirtualPortgroup):
                dvs_list.append(pg)
            else:
                vss_list.append(pg)

        if len(dvs_list) > 1:
            logging.warning(f"in select_portgroup, found {len(dvs_list)} dvs in result list")
        if len(vss_list) > 1:
            logging.warning(f"in select_portgroup, found {len(vss_list)} vss in result list")

        if len(dvs_list) == 0 and len(vss_list) == 0:
            return None

        if len(dvs_list) > 0 and dvs_skew:
            return dvs_list[0]
        elif len(vss_list) > 0:
            return vss_list[0]
        elif len(dvs_list) > 0:
            return dvs_list[0]
        else:
            logging.warning("unknown status in select_portgroup")
            return None

    @staticmethod
    def find_parent_resource(obj, parent_type):
        """往上追溯制定类型的父级对象。
        
        Args:
            obj: 开始追溯的起点实例。
            parent_type: 指定追溯的父级类型，由 vim 中支持。
        Returns:
            <vim.*>: 遍历结果对象。
        """
        _max_recursion_depth = 5

        obj_found = obj
        for i in range(_max_recursion_depth):
            if isinstance(obj_found, parent_type):
                return obj_found
            if not hasattr(obj_found, "parent"):
                return None
            obj_found = obj_found.parent

        logging.debug(f"out of _max_recursion_depth {_max_recursion_depth} in find_parent_resource")
        return None

    @staticmethod
    def find_child_entities(obj, type_, depth, objs_found=[]):
        if depth < 0:
            return objs_found
        if isinstance(obj, type_):
            objs_found.append(obj)
            return 
        if not hasattr(obj, "childEntity"):
            return 

        for e in obj.childEntity:
            if isinstance(e, vim.Folder):
                VBaseLib.find_child_entities(e, type_, depth-1, objs_found)
            if isinstance(e, type_):
                objs_found.append(e)

        return 

    @staticmethod
    def is_host(obj):
        return isinstance(obj, vim.HostSystem)

    @staticmethod
    def wait_for_task(task, chk_interval):
        """轮询等待任务的检查函数。

        Args:
            task: pyvmomi 任务实例。
            chk_interval: 检查间隔，单位为秒。
        Returns:
            <bool>: 任务是否正常完成。
        """
        doflag = False
        try:
            while 1:
                state = task.info.state
                queue_times = TASK_QUEUED_TIMS
                if state == vim.TaskInfo.State.success:
                    logging.info("the progress of task is [{!s}%]".format(task.info.progress))
                    logging.info("the task is successful")
                    return True
                elif state == vim.TaskInfo.State.error:
                    logging.error("the task is error")
                    logging.error("task Error Message:[{!s}]".format(task.info.error.msg))
                    logging.error("task Error Descritpion:[{!s}]".format(task.info.description.message))
                    return False
                elif state == vim.TaskInfo.State.running:
                    logging.debug("the progress of task is [{!s}%]".format(task.info.progress))
                    logging.debug("the task is running")
                    time.sleep(chk_interval)
                elif state == vim.TaskInfo.State.queued:
                    logging.warning("the task is queued")
                    if queue_times < 0:
                        logging.error("out of TASK_QUEUED_TIMS: [{!s}], exit the task, please check it".format(TASK_QUEUED_TIMS))
                        return False

                    queue_times -= 1
                    time.sleep(chk_interval)
                else:
                    logging.error("the task state is UNKNOW: [{!s}]".format(state))
                    return False
        except Exception as e:
            logging.error("the task target unknow error")
            if hasattr(e, "msg"):
                logging.error("the error:{!s}".format(e.msg))
            return False

    @staticmethod
    def get_cuskey_tracing(service_instance):
        """获取自定义属性的字段追踪表。
        """
        tracing = {}
        m = service_instance.content.customFieldsManager
        for f in m.field:
            tracing[f.name] = f.key
        return tracing