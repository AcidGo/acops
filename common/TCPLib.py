import socket

class TCPLib(object):
    @staticmethod
    def tcp_test(host, port, timeout=5):
        """
        """
        socks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socks.settimeout(timeout)
        try:
            rc = socks.connect_ex((host, port))
        except Exception as e:
            logging.error("get an error when test tcp: {!s}:{!s}".format(host, str(port)))
            rc = -999
        finally:
            socks.close()
        return True if rc == 0 else False