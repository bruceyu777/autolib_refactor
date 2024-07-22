import sys
import time

from lib.services.environment import env
from lib.services.log import logger
from lib.utilities.exceptions import ItemNotDefined, ResourceNotAvailable

from .kvm import KVM

VM_RUNNING = "running"
VM_SHUTOFF = "shut off"
VM_PAUSED = "paused"

KVM_DEFAULT_IMAGE_FOLDER = r"/home/tester/images/another"


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
            raise ItemNotDefined(f"{self.vm_name}:VM_TYPE")

        self.params["memory"] = self.VM_SPECS[vm_type]["memory"]
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
        if not nics:
            if self.host.get_cfg("non_sriov", "no") == "yes":
                error = f"\nRequire NIC_LIST for {self.vm_name} while NON_SRIOV was set!\n"
                raise ResourceNotAvailable(error)
            else:
                return ""

        return "".join(template.format(dev) for dev in nics.strip().split())

    def _pre_pci_dev_list(self):

        temp = "--host-device=pci_{} "
        pci_dev = self.host.get_cfg("pci_id_list", "")
        if pci_dev:
            # print("pci_dev is ", pci_dev)
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
        # print("port_list is", port_list)
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
        image_location = self.host.prepare_image(
            self.vm_name, self.release, self.build
        )
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


class VmManager:
    def __init__(self, vms):
        self.vm_hosts = dict()
        self.hosts = dict()
        for vm in vms:
            self.add_vm(vm)

    def add_vm(self, vm_name):
        host_name = env.get_vm_host(vm_name)
        if host_name.startswith("KVM"):
            if host_name not in self.hosts:
                self.hosts[host_name] = KVM(host_name)
            self.vm_hosts[vm_name] = self.hosts[host_name]
        else:
            raise NotImplementedError

    def create_vm(self, vm_name, release, build):
        vm_status = self.retr_vm_status(vm_name)
        if vm_status:
            if vm_status == VM_RUNNING:
                self.poweroff_vm(vm_name)
                self.destroy_vm(vm_name)
            if vm_status in [VM_SHUTOFF, VM_PAUSED]:
                self.destroy_vm(vm_name)
        host = self.vm_hosts[vm_name]
        VmBuilder(host, vm_name, release, build).create_vm()

    def poweron_vm(self, vm_name):
        self.vm_hosts[vm_name].power_on_vm(vm_name)

    def poweroff_vm(self, vm_name):
        self.vm_hosts[vm_name].power_off_vm(vm_name)

    def destroy_vm(self, vm_name):
        self.vm_hosts[vm_name].remove_vm(vm_name)

    def retr_vm_status(self, vm_name):
        return self.vm_hosts[vm_name].retr_vm_status(vm_name)

    def deploy_vms(self):
        release, build = env.args.release, env.args.build
        if not all([release, build]):
            logger.error(
                "Release and build must be specified for deploying vms."
            )
            sys.exit(-1)

        for vm in self.vm_hosts:
            logger.notify("Start creating %s.", vm)
            self.create_vm(vm, release, build)
            self.poweron_vm(vm)
            logger.notify("%s is created.", vm)

    def make_vms_ready(self):
        for vm_name in self.vm_hosts:
            vm_status = self.retr_vm_status(vm_name)
            if vm_status is None:
                raise ResourceNotAvailable(f"vm_name {vm_name} not available")
            if vm_status == VM_RUNNING:
                continue
            if vm_status in [VM_SHUTOFF, VM_PAUSED]:
                self.poweron_vm(vm_name)

    def setup_vms(self):
        if env.need_deploy_vm():
            self.deploy_vms()
            return
        self.make_vms_ready()
