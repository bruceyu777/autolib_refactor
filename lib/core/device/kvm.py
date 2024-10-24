import os
import re
import time
from enum import Enum

from lib.services.image_server import Image, image_server
from lib.services.log import logger
from lib.utilities.exceptions import ImageDownloadErr, ResourceNotAvailable

from .computer import Computer
from .computer_conn import ComputerConn
from .vm_builder import VmBuilder

KVM_DEFAULT_IMAGE_FOLDER = r"/home/tester/images/another"
VIRSH_DEFAULT_TIMEOUT = 60 * 2


class VmStatus(Enum):
    RUNNING = "running"
    SHUTOFF = "shut off"
    PAUSED = "paused"

    @classmethod
    def all_statuses(cls):
        return [status.value for status in cls]


class KVM(Computer):
    def __init__(self, dev_name):
        super().__init__(dev_name)
        self.image_location = None
        self.hosted_vms = []

    def force_login(self):
        raise NotImplementedError

    def get_dev_name(self):
        return self.dev_name

    def _compose_conn(self):
        ip = self.dev_cfg["management"]
        proto = self.dev_cfg.get("access_protocol", "SSH")
        port = self.dev_cfg.get("access_port", "22")
        if proto.upper() != "SSH":
            raise NotImplementedError
        username = self.dev_cfg["user_name"]
        return f"ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p {port} {username}@{ip}"

    def connect(self):
        self.conn = ComputerConn(
            self.dev_name,
            self._compose_conn(),
            self.dev_cfg["user_name"],
            self.dev_cfg["password"],
        )
        self.send_command("")
        self.clear_buffer()

    def get_cfg(self, item_name, default_value=None):
        return self.dev_cfg.get(item_name, default_value)

    def model(self, vm_name):
        return "FGT_VM64_KVM" if vm_name.startswith("FVM") else "FFW_VM64_KVM"

    def prepare_image(self, vm_name, release, build):
        image = Image(self.model(vm_name), release, build)
        image_url = image_server.get_image_http_url(image)
        image_name = image_url.split("/")[-1]
        command = f"curl {image_url} --output {image_name}"
        self.send_command(command, timeout=60)
        self.image_location = self.unzip_image(image_name)
        if not self.image_location:
            raise ImageDownloadErr("Unable to unzip '{image_name}'")
        logger.debug("<<< image_location: '%s'", self.image_location)
        return self.image_location

    def unzip_image(self, zipped_image, remove_flag=True):
        """
        root@ubuntu-kvm:~# unzip FOS_VM64_KVM-v6-build0763-FORTINET.deb.kvm.zip
        Archive:  FOS_VM64_KVM-v6-build0763-FORTINET.deb.kvm.zip
        inflating: fortios.qcow2
        """
        template = ">>> zipped_image: '%s', remove_flag: '%s'"
        logger.debug(template, zipped_image, remove_flag)
        sub_folder = str(int(time.time()))
        target = os.path.join(KVM_DEFAULT_IMAGE_FOLDER, sub_folder)
        command = "unzip -o {} -d {}".format(zipped_image, target)

        match, _ = self.send_command(
            command, r"inflating: (?P<image_name>.*)\n", timeout=600
        )

        image_name = match.group("image_name").strip().replace("\n", "")

        self.image_location = os.path.join(target, image_name)
        if remove_flag:
            command = "rm -f %s" % zipped_image
            self.send_command(command)
        logger.debug("<<< image_name: '%s'", image_name)
        return image_name

    def get_mgmt_nic(self):
        r"""
        root@kvm-server:/home/zdl/autolib# ip -o -4 addr show  | grep 10.6.30.139 --color=never
        5: br0    inet 10.6.30.139/24 brd 10.6.30.255 scope global br0\       valid_lft forever preferred_lft forever
        """
        mgmt_ip = self.dev_cfg.get("management")
        command = f"ip -o addr show | grep {mgmt_ip}/ --color=never"
        _, ret = self.send_command(command, timeout=10)
        matched_nics = re.findall(r":\s+([^\s]+)\s+inet", ret, flags=re.M)

        if not matched_nics:
            logger.error("\nUnable to get management nic with IP(%s)!!!\n", mgmt_ip)
            raise ResourceNotAvailable(
                f"\nUnable to get management nic with IP({mgmt_ip})!!!\n"
            )
        mgmt_nic = matched_nics[0]
        logger.debug("mgmt_nic set to be: %s", mgmt_nic)
        return mgmt_nic

    def create_a_disk(self, saveas, block_size="1G", count=32, disk_size="32G"):
        template = ">>> saveas: '%s', block_size: '%s', count: '%s', disk_size: '%s'"
        logger.debug(template, saveas, block_size, count, disk_size)
        if not saveas.startswith(KVM_DEFAULT_IMAGE_FOLDER):
            saveas = os.path.join(KVM_DEFAULT_IMAGE_FOLDER, os.path.basename(saveas))
        command = "sudo qemu-img create -f raw {} {}".format(saveas, disk_size)
        match, _ = self.send_command(command, r"[$]$", timeout=10)
        logger.info("\nLog disk file is created: %s\n", saveas)
        logger.debug("<<< return: '%s', saveas: '%s'", match, saveas)
        return match, saveas

    def prepare_for_vm_deployment(self, vm_name):
        vm_status = self.retr_vm_status(vm_name)
        if vm_status:
            if vm_status is VmStatus.RUNNING:
                self.power_off_vm(vm_name)
                self.remove_vm(vm_name)
            if vm_status in (VmStatus.PAUSED, VmStatus.SHUTOFF):
                self.remove_vm(vm_name)

    def make_vm_ready(self, vm_name):
        status = self.retr_vm_status(vm_name)
        if status is None:
            raise ResourceNotAvailable(f"vm_name {vm_name} not available")
        if status in (VmStatus.PAUSED, VmStatus.SHUTOFF):
            self.power_on_vm(vm_name)

    def retr_vm_status(self, vm_name):
        supported_status = VmStatus.all_statuses()
        match_rule = rf"\S+\s*{vm_name}\s*(?P<status>{'|'.join(supported_status)})"
        list_vm_cmd = "virsh list --all"
        match, _ = self.send_command(list_vm_cmd, match_rule, timeout=10)
        return VmStatus(match.group("status")) if match else None

    def deploy_vm(self, vm_name, release, build):
        self.prepare_for_vm_deployment(vm_name)
        VmBuilder(self, vm_name, release, build).create_vm()
        time.sleep(2)
        self.power_on_vm(vm_name)
        self.wait_until_running(vm_name)

    def wait_until_running(self, vm_name, time_out=10 * 60):
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < time_out:
            if self.retr_vm_status(vm_name) is VmStatus.RUNNING:
                break
            time.sleep(2)
        else:
            raise ResourceNotAvailable(
                f"vm '{vm_name}' not ready after '{time_out}'s!!"
            )

    def power_on_vm(self, vm_domain):
        command = f"virsh --connect qemu:///system start {vm_domain}"
        expected_str = rf"Domain {vm_domain} started"
        return self.send_command(command, expected_str, timeout=VIRSH_DEFAULT_TIMEOUT)

    def power_off_vm(self, vm_domain, poweroffdelay=10):
        command = f"virsh shutdown {vm_domain}"
        expected_str = rf"Domain '{vm_domain}' is being shutdown"
        self.send_command(command, expected_str, timeout=VIRSH_DEFAULT_TIMEOUT)
        time.sleep(poweroffdelay)
        vm_status = self.retr_vm_status(vm_domain)
        return vm_status is None or vm_status is VmStatus.SHUTOFF

    def remove_vm(self, vm_domain):
        command = f"virsh undefine {vm_domain}"
        expected_str = rf"Domain '{vm_domain}' has been undefined"
        return self.send_command(command, expected_str, timeout=VIRSH_DEFAULT_TIMEOUT)

    def create_vm(self, **kwargs):
        template = (
            "sudo virt-install --name {vm_domain} "
            + "--ram {memory} --vcpus {vcpu} "
            + "--disk path={image_location},size=100,format={image_type},bus=virtio,cache=none "
            + "{logdisk}"
            + "--network type={network_type},source={mgmt_nic},model=virtio "
            + "--serial tcp,host={serial_ip}:{serial_port},mode=bind,protocol={con_protocol} "
            + "{port_list} --osinfo detect=off,require=off "
            + "--import --noreboot --noautoconsole --wait=1 --metadata uuid={uuid}"
        )

        command = template.format(**kwargs)
        expected_str = "Domain creation completed"
        self.send_command(command, expected_str, timeout=VIRSH_DEFAULT_TIMEOUT)
        return command
