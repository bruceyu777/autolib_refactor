import sys

from lib.services.environment import env
from lib.services.log import logger

from .kvm import KVM

KVM_DEFAULT_IMAGE_FOLDER = r"/home/tester/images/another"


class VmManager:
    supported_hypervisor = {"KVM"}
    hypervisor_class = {"KVM": KVM}

    def __init__(self, vms):
        self.vm_hosts = {}
        self.hosts = {}
        for vm in vms:
            self.add_vm(vm)

    def init_host(self, host_name):
        hypervisor_type = host_name.split("_")[0]
        if hypervisor_type not in self.supported_hypervisor:
            raise NotImplementedError
        init_class = self.hypervisor_class[hypervisor_type]
        return init_class(host_name)

    def add_vm(self, vm_name):
        host_name = env.get_vm_host(vm_name)
        if host_name not in self.hosts:
            self.hosts[host_name] = self.init_host(host_name)
        self.vm_hosts[vm_name] = self.hosts[host_name]

    def power_on_vm(self, vm_name):
        self.vm_hosts[vm_name].power_on_vm(vm_name)

    def power_off_vm(self, vm_name):
        self.vm_hosts[vm_name].power_off_vm(vm_name)

    def remove_vm(self, vm_name):
        self.vm_hosts[vm_name].remove_vm(vm_name)

    def retr_vm_status(self, vm_name):
        return self.vm_hosts[vm_name].retr_vm_status(vm_name)

    def deploy_vms(self):
        release, build = env.args.release, env.args.build
        if not all([release, build]):
            logger.error("Release and build must be specified for deploying vms.")
            sys.exit(-1)

        for vm_name, host in self.vm_hosts.items():
            host.deploy_vm(vm_name, release, build)

    def make_vms_ready(self):
        for vm_name, host in self.vm_hosts.items():
            host.make_vm_ready(vm_name)

    def setup_vms(self):
        if env.need_deploy_vm():
            self.deploy_vms()
            return
        self.make_vms_ready()
