import re
import subprocess

from lib.services import logger

from .dev_conn import DevConn


class FosConn(DevConn):
    def _normalize_conn_parameters(self):
        # disable SSH strict host key checking
        super()._normalize_conn_parameters()
        if not any(x in self.conn for x in ["ssh", "telnet"]):
            self.conn = f"telnet {self.conn}"


class VmSerialConn(FosConn):

    def connect(self):
        port_number = int(re.search(r"\s(\d+)$", self.conn).group(1))
        VmSerialConn.kill_process_on_port(port_number)
        return super().connect()

    @staticmethod
    def kill_process_on_port(port: int) -> None:
        try:
            result = subprocess.run(
                ["pkill", "-f", f"telnet.*{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            logger.debug("kill telnet session(on port: %d):\n %s", port, result.stdout)
        except subprocess.CalledProcessError as e:
            logger.debug("Error killing process on port %d(%s)", port, str(e))


class PhySerialConn(FosConn):
    pass


class SSHConn(FosConn):
    pass


def get_session_init_class(is_serial_connection, is_virtual_machine):
    if is_serial_connection:
        return VmSerialConn if is_virtual_machine else PhySerialConn
    return SSHConn
