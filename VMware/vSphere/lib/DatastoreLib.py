class DatastoreLib(object):
    @staticmethod
    def has_support_fs(ds, support_list):
        # TODO: 深入到 ds 的 type 作区分
        for i in support_list:
            if hasattr(ds.info, i):
                return True
        return False