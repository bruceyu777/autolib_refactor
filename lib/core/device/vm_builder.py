import time

from lib.services.environment import env
from lib.utilities.exceptions import ResourceNotAvailable


class VmBuilder:
    VM_SPECS = {
        "VM01": {"memory": 2 * 1024, "vcpu": 1},
        "VM02": {"memory": 4 * 1024, "vcpu": 2},
        "VM04": {"memory": 6 * 1024, "vcpu": 4},
        "VM08": {"memory": 12 * 1024, "vcpu": 8},
        "VM16": {"memory": 24 * 1024, "vcpu": 16},
        "VM32": {"memory": 48 * 1024, "vcpu": 32},
        "VMUL": {"memory": 96 * 1024, "vcpu": 64},
    }

    def __init__(self, host, vm_name, release, build):
        self.host = host
        self.params = {"vm_domain": vm_name}
        self.vm_name = vm_name
        self.vm_cfg = env.get_dev_cfg(vm_name)
        self.release = release
        self.build = build

    def _calc_cpu_mem(self):
        vm_type = self.vm_cfg.get("vm_type", None)
        if vm_type is None:
            raise ResourceNotAvailable(
                f"Unable to locate VM_TYPE in conf for {self.vm_name}"
            )
        self.params["memory"] = self.vm_cfg.get(
            "memory", self.VM_SPECS[vm_type]["memory"]
        )
        self.params["vcpu"] = self.VM_SPECS[vm_type]["vcpu"]

    def _pre_nic_dev_list(
        self,
        driver_queues,
        ntype="bridge",
        model="virtio",
        source_mode="passthrough",
    ):
        tmp = "--network source={},source_mode=%s,driver_queues=%s,model=%s,type=%s "
        template = tmp % (source_mode, driver_queues, model, ntype)
        nics = self.host.get_cfg("nic_list", "")
        if nics:
            return "".join(template.format(dev) for dev in nics.strip().split())
        if self.host.get_cfg("non_sriov", "no") == "yes":
            error = f"\nRequire NIC_LIST for {self.vm_name} while NON_SRIOV was set!\n"
            raise ResourceNotAvailable(error)
        return ""

    def _pre_pci_dev_list(self):
        temp = "--host-device=pci_{} "
        pci_dev = self.host.get_cfg("pci_id_list", "")
        if pci_dev:
            return "".join(
                temp.format(dev.replace(":", "_").replace(".", "_"))
                for dev in pci_dev.split()
            )
        return ""

    def _calc_portlist(self):
        if self.host.get_cfg("non_sriov", "no") == "yes":
            port_list = self._pre_nic_dev_list(self.params["vcpu"])
        else:
            port_list = self._pre_pci_dev_list()
        self.params["port_list"] = port_list

    def gen_log_disk_file_name(self, disksize=30):
        timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        diskfile = "{}_{}_{}.qcow2".format(self.vm_name, disksize, timestamp)
        return diskfile

    @staticmethod
    def _compose_disk_cli(
        diskfile, disksize, disk_format="qcow2", diskbus="virtio", cache="none"
    ):
        cli = "--disk path={},size={},format={},bus={},cache={} "
        return cli.format(diskfile, disksize, disk_format, diskbus, cache)

    def _create_log_disk(self):
        disk_size = self.vm_cfg.get("log_disk_size", 30)
        disk_size = round(float(disk_size), 2)
        disk_file_name = self.gen_log_disk_file_name(disk_size)
        _, disk_img = self.host.create_a_disk(
            disk_file_name, disk_size="{}G".format(disk_size)
        )
        log_disk = self._compose_disk_cli(disk_img, disk_size)
        self.params["logdisk"] = log_disk

    def _prepare_image(self):
        image_location = self.host.prepare_image(self.vm_name, self.release, self.build)
        self.params["image_location"] = image_location
        self.params["image_type"] = image_location.split(".")[-1]

    def _get_console_access_info(self):
        conn = self.vm_cfg.get("connection")
        ip, port = conn.split()
        self.params["serial_ip"] = ip
        self.params["serial_port"] = port
        self.params["con_protocol"] = "telnet"

    def create_vm(self):
        self._prepare_image()
        self._calc_cpu_mem()
        self._calc_portlist()
        self._create_log_disk()
        self._get_console_access_info()
        self.params.update(
            {
                "mgmt_nic": self.host.get_mgmt_nic(),
                "network_type": self.host.get_cfg("network_type", "direct"),
                "uuid": self.vm_cfg.get("uuid", None),
            }
        )
        self.host.create_vm(**self.params)
