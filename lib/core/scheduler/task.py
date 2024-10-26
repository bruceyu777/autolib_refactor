import os
import time
from pathlib import Path
from time import perf_counter

from lib.services import env, logger, oriole, summary
from lib.utilities.exceptions import FileNotExist, GeneralException, NotSupportedDevice

from ..compiler.compiler import compiler
from ..device.forti_vm import FortiVM
from ..device.fortigate import FortiGate
from ..device.pc import Pc
from ..device.vm_manager import VmManager
from ..executor.executor import Executor


class Task:
    def __init__(self, script):
        if not os.path.exists(script):
            raise FileNotExist(script)
        self.script = script
        self.devices = {}

    def setup_vms(self):
        vms = [dev_name for dev_name in self.devices if env.is_vm_device(dev_name)]
        vm_manager = VmManager(vms)
        vm_manager.setup_vms()

    def restore_image(self):
        if not all([env.args.release, env.args.build]):
            logger.info("Test with the current loaded images.")
            return

        for dev_name, dev in self.devices.items():
            if env.is_fos_device(dev_name) and not env.need_deploy_vm():
                dev.restore_image(
                    env.args.release, env.args.build, env.args.reset, env.args.burn
                )

    def init_devices(self):
        logger.debug("Devices used during the test %s", list(self.devices.keys()))
        for dev_name in self.devices:
            t1 = perf_counter()
            if env.is_vm_device(dev_name):
                self.devices[dev_name] = FortiVM(dev_name)
            elif dev_name.startswith("FGT"):
                self.devices[dev_name] = FortiGate(dev_name, env.args.burn)
            elif dev_name.startswith("PC"):
                self.devices[dev_name] = Pc(dev_name)
            else:
                raise NotSupportedDevice(dev_name)
            t2 = perf_counter()
            logger.info("Setting up device %s takes %d s", dev_name, t2 - t1)
            t1 = t2

    def compose_involved_devices(self):
        devices = compiler.devices
        dut = env.get_dut()
        if dut:
            devices.add(env.get_dut())
        self.devices = {dev_name: None for dev_name in devices}

    def setup_devices(self):
        self.compose_involved_devices()
        self.setup_vms()
        self.init_devices()
        self.restore_image()
        self.activate_vm_licenses()

    def activate_vm_licenses(self):
        vms = [dev_name for dev_name in self.devices if env.is_vm_device(dev_name)]
        if vms and env.need_deploy_vm():
            logger.info(
                "Sleep 10s for the console to able to be connected for new deployed vms."
            )
            time.sleep(10)
            for vm in vms:
                self.devices[vm].activate_license()

    def compile(self):
        raise NotImplementedError

    def keepalive_devices(self):
        if env.need_keep_alive():
            for dev in self.devices:
                try:
                    dev.send_line("")
                except Exception as _:
                    logger.error("Failed to send keep alive message.")

    def _start_record_terminal(self, script_id):
        for dev in self.devices.values():
            logger.debug("Start record terminal for %s", dev)
            dev.start_record_terminal(script_id)

    def _stop_record_terminal(self, _):
        for dev in self.devices.values():
            dev.stop_record_terminal()

    def _record_testing_script(self, script_id):
        env.add_var("testing_script", script_id)

    def _clear_testing_script(self):
        env.clear_var("testing_script")

    def execute_script(self, script, vm_codes, devices):
        script_id = Path(script).stem
        start = perf_counter()
        summary.update_testscript(script_id, "Testing")
        self._record_testing_script(script_id)
        self._start_record_terminal(script_id)
        with Executor(script, vm_codes, devices) as executor:
            executor.execute()
        self._stop_record_terminal(script_id)
        end = perf_counter()
        duration = int(end - start)
        summary.update_testscript_duration(script_id, duration)

    def execute(self):
        raise NotImplementedError

    def summary(self):
        summary.show_summary()
        oriole.dump()

    def run(self, args):
        t1 = perf_counter()
        self.compile()
        t2 = perf_counter()
        if args.check:
            return
        self.setup_devices()
        t3 = perf_counter()
        try:
            self.execute()
        except GeneralException:
            logger.exception("Task Execution Failure...")
        finally:
            t4 = perf_counter()
            if args.submit_flag != "none":
                oriole.submit()
            self.summary()
            t5 = perf_counter()
            logger.debug("Compiling takes %.1f s ", t2 - t1)
            logger.debug("Setting up devices takes %.1f s", t3 - t2)
            logger.debug("Executing testcases takes %.1f s", t4 - t3)
            logger.debug("Generating summary report takes %.1f s", t5 - t4)
