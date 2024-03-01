import os
import re
import time

from lib.services.environment import env
from lib.services.image_server import TFTP_SERVER_IP, Image, image_server
from lib.services.log import logger
from lib.utilities.exceptions import ImageDownloadErr, ImageNotFound

from .computer import Computer
from .computer_conn import ComputerConn

KVM_DEFAULT_IMAGE_FOLDER = r"/home/tester/images/another"


VM_PAUSED = "paused"
VM_SHUTOFF = "shut off"


class KVM(Computer):
    def __init__(self, dev_name):
        self.dev_name = dev_name
        self.dev_cfg = env.get_dev_cfg(dev_name)
        super().__init__(dev_name)
        self.image_location = None
        self.hosted_vms = []

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
        # breakpoint()
        image = Image(self.model(vm_name), release, build)
        image_file = image_server.lookup_image(image)
        if not image_file:
            raise ImageNotFound(image)
        image_location = image_file["parent_dir"]
        image_name = image_file["name"]

        command = f"curl http://{TFTP_SERVER_IP}/{image_location}/{image_name} --output {image_name}"

        self.send_command(command, timeout=60)

        image = self.unzip_image(image_name)
        ok_flag = self.chwon_file(image)
        if ok_flag and image:
            self.image_location = image
        else:
            raise ImageDownloadErr(image_name)
        # self.send_command("\n")
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

    def chwon_file(self, image):
        logger.debug(">>> image: '%s'", image)
        command = "chown tester:tester {}".format(image)
        match, _ = self.send_command(command)
        logger.debug("<<< return: '%s'", match)
        return match

    def get_mgmt_nic(self):
        """
        root@ubuntu-kvm:~# ifconfig | grep 172.18.53.151 -B 3  --color=never
                TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

        eno3: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                inet 172.18.53.151  netmask 255.255.255.0  broadcast 172.18.53.255
        [root@dublin /root]# ifconfig
        eth0      Link encap:Ethernet  HWaddr 00:B0:D0:D8:FE:09
          inet addr:132.177.8.28  Bcast:132.177.8.127  Mask:255.255.255.128
        """
        mgmt_ip = self.dev_cfg.get("management")
        command = f"ifconfig | grep {mgmt_ip} -B 3 --color=never"
        _, ret = self.send_command(command, r".*(flags=|encap:).*", timeout=10)
        mgmt_nic = None
        m = re.search(r"^(?P<nic>\S+):\s+flags=.*$", ret, re.M)
        if m:
            mgmt_nic = m.group("nic")
        else:
            m = re.search(r"^(?P<nic>\S+)\s+Link encap:.*$", ret, re.M)
            if m:
                mgmt_nic = m.group("nic")

        if mgmt_nic is None:
            logger.error("\nUnable to get management nic!!!\n")
            mgmt_nic = "Unknown"

        logger.debug("mgmt_nic set to be: %s", mgmt_nic)
        return mgmt_nic

    def create_a_disk(self, saveas, block_size="1G", count=32, disk_size="32G"):
        template = ">>> saveas: '%s', block_size: '%s', count: '%s', disk_size: '%s'"
        logger.debug(template, saveas, block_size, count, disk_size)
        if not saveas.startswith(KVM_DEFAULT_IMAGE_FOLDER):
            saveas = os.path.join(KVM_DEFAULT_IMAGE_FOLDER, os.path.basename(saveas))
        if disk_size:
            command = "sudo qemu-img create -f raw {} {}".format(saveas, disk_size)
        elif block_size and count:
            command = "dd if=/dev/zero of={} bs={} count={}".format(
                saveas, block_size, count
            )
        match, _ = self.send_command(command, r"[$]$", timeout=10)
        logger.info("\nLog disk file is created: %s\n", saveas)
        logger.debug("<<< return: '%s', saveas: '%s'", match, saveas)
        return match, saveas

    def retr_vm_status(self, vm_name):
        match_rule = rf"\S+\s*{vm_name}\s*(?P<status>running|paused|shut off)"
        list_vm_cmd = "virsh list --all"
        match, _ = self.send_command(list_vm_cmd, match_rule, timeout=10)
        return match.group("status") if match else None

    def power_on_vm(self, vm_domain):
        command = f"virsh --connect qemu:///system start {vm_domain}"
        expected_str = rf"Domain {vm_domain} started"
        return self.send_command(command, expected_str)

    def power_off_vm(self, vm_domain, poweroffdelay=10):
        command = f"virsh shutdown {vm_domain}"
        expected_str = rf"Domain {vm_domain} is being shutdown"
        self.send_command(command, expected_str)
        time.sleep(poweroffdelay)
        vm_status = self.retr_vm_status(vm_domain)
        return vm_status is None or vm_status in [VM_PAUSED, VM_SHUTOFF]

    def remove_vm(self, vm_domain):
        command = f"virsh undefine {vm_domain}"
        expected_str = rf"Domain {vm_domain} has been undefined"
        return self.send_command(command, expected_str)

    def create_vm(self, **kwargs):
        template = (
            "sudo virt-install --name {vm_domain} "
            + "--ram {memory} --vcpus {vcpu} "
            + "--disk path={image_location},size=100,format={image_type},bus=virtio,cache=none "
            + "{logdisk}"
            + "--network type={network_type},source={mgmt_nic},model=virtio "
            + "--serial tcp,host={serial_ip}:{serial_port},mode=bind,protocol={con_protocol} "
            + "{port_list} "
            + "--import --noreboot --noautoconsole --wait=1 --metadata uuid={uuid}"
        )

        command = template.format(**kwargs)
        expected_str = "Domain creation completed"
        self.send_command(command, expected_str)

        return command
