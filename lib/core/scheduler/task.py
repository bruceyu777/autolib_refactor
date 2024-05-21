import time
from pathlib import Path
from time import perf_counter

from lib.services import env, logger, oriole, summary
from lib.utilities.exceptions import NotSupportedDevice

from ..compiler.compiler import compiler
from ..device.forti_vm import FortiVM
from ..device.fortigate import FortiGate
from ..device.pc import Pc
from ..device.vm_manager import VmManager
from ..executor.executor import Executor


class Task:
    def __init__(self, script):
        self.script = script

        self.devices = dict()

    def setup_vms(self):
        vms = [
            dev_name
            for dev_name in self.devices
            if dev_name.startswith(("FVM", "FFW"))
        ]
        vm_manager = VmManager(vms)
        vm_manager.setup_vms()

    def restore_image(self):
        if not all([env.args.release, env.args.build]):
            logger.info("Test with the current loaded images.")
            return

        for dev_name, dev in self.devices.items():
            if dev_name.startswith(("FVM", "FFW", "FGT")) and not env.need_deploy_vm():
                dev.restore_image(env.args.release, env.args.build, env.args.reset)
            if dev_name.startswith(("FVM", "FFW")) and env.need_deploy_vm():
                dev.activate_license()

    def init_devices(self):
        logger.notify("Devices used during the test %s", list(self.devices.keys()))

        if env.need_deploy_vm() and any(dev_name.startswith(("FVM", "FFW")) for dev_name in self.devices):
            logger.notify("Sleep 10s for the console to abel to be connected for new deployed vms.")
            time.sleep(10)
        for dev_name in self.devices:
            t1 = perf_counter()
            if dev_name.startswith(("FVM", "FFW")):
                self.devices[dev_name] = FortiVM(dev_name)
            elif dev_name.startswith("FGT"):
                self.devices[dev_name] = FortiGate(dev_name)
            elif dev_name.startswith("PC"):
                self.devices[dev_name] = Pc(dev_name)
            else:
                raise NotSupportedDevice(dev_name)
            t2 = perf_counter()
            logger.info(f"Setting up device {dev_name} takes {t2-t1} s")
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
            logger.info("Start record terminal for %s", dev)
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
        # env.add_var("testing_script", script_id)
        # print("script is tested.")
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
        self.execute()
        t4 = perf_counter()
        if args.submit_flag != "none":
            oriole.submit()
        self.summary()
        t5 = perf_counter()
        logger.notify("Compiling takes %s s ", t2 - t1)
        logger.notify("Setting up devices takes %s s", t3 - t2)
        logger.notify(f"Executing testcases takes %s s", t4 - t3)
        logger.notify(f"Generating summary report takes %s s", t5-t4)
