import time
from time import perf_counter

from lib.core.compiler import Script
from lib.core.device import FortiAP, FortiGate, FortiVM, Pc, VmManager
from lib.core.executor import Executor
from lib.services import TestStatus, env, logger, oriole, summary
from lib.utilities import GeneralException, NotSupportedDevice, sleep_with_progress


class Task:

    script_init_class = Script

    def __init__(self, script, non_strict_mode=True):
        self.non_strict_mode = non_strict_mode
        self.script = self.script_init_class(script)
        self.devices = {}

    @staticmethod
    def setup_vms(vms):
        vm_manager = VmManager(vms)
        vm_manager.setup_vms()
        if env.need_deploy_vm():
            sleep_with_progress(20)

    def restore_image(self):
        release, build, factory_reset, burn_image = env.get_restore_image_args()
        if not release or not build:
            logger.info("Test with the current loaded images.")
            return

        for dev_name, dev in self.devices.items():
            if env.is_fos_device(dev_name) and not env.need_deploy_vm():
                dev.restore_image(release, build, factory_reset, burn_image)

    def get_init_class(self, dev_name):
        if env.is_vm_device(dev_name):
            return FortiVM
        if dev_name.startswith("FGT"):
            if env.is_running_on_vm():
                return FortiVM
            return FortiGate
        if dev_name.startswith("PC"):
            return Pc
        if dev_name.startswith("FAP"):
            return FortiAP
        raise NotSupportedDevice(dev_name)

    def init_devices(self):
        logger.debug("Devices used during the test %s", list(self.devices.keys()))
        for dev_name in self.devices:
            t1 = perf_counter()
            init_class = self.get_init_class(dev_name)
            device = init_class(dev_name)
            self.devices[dev_name] = device
            t2 = perf_counter()
            logger.info("Setting up device %s takes %d s", dev_name, t2 - t1)
            t1 = t2
        self._attach_controller_to_fap()

    def _attach_controller_to_fap(self):
        for dev_name, dev_instance in self.devices.items():
            if not isinstance(dev_instance, FortiAP):
                continue
            controller_name = env.get_fap_controller(dev_name)
            if controller_name:
                controller_instance = self.devices.get(controller_name)
                dev_instance.set_controller(controller_instance)

    def get_all_devices(self):
        devices = self.script.get_all_involved_devices()
        dut = env.get_dut()
        if dut:
            devices.add(env.get_dut())
        controllers = filter(None, (env.get_fap_controller(dev) for dev in devices))
        devices = devices.union(controllers)
        return devices

    def compose_involved_devices(self):
        devices = self.get_all_devices()
        self.devices = {dev_name: None for dev_name in devices}

    def setup_devices(self):
        self.compose_involved_devices()
        vms = [dev_name for dev_name in self.devices if env.is_vm_device(dev_name)]
        if vms:
            Task.setup_vms(vms)
        self.init_devices()
        self.restore_image()
        if vms:
            self.activate_vm_licenses(vms)

    def activate_vm_licenses(self, vms):
        if env.need_deploy_vm():
            logger.info(
                "Sleep 10s for the console to able to be connected for new deployed vms."
            )
            time.sleep(10)
            for vm in vms:
                self.devices[vm].activate_license()

    def compile(self):
        summary.add_testscript(self.script)

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

    def execute_script(self, script, devices):
        start = perf_counter()
        summary.update_testscript(script.id, TestStatus.TESTING)
        self._record_testing_script(script.id)
        self._start_record_terminal(script.id)
        try:
            with Executor(script, devices) as executor:
                executor.execute()
        except Exception:
            summary.update_testscript(script.id, TestStatus.FAILED)
            raise
        finally:
            self._stop_record_terminal(script.id)
            end = perf_counter()
            duration = int(end - start)
            summary.update_testscript_duration(script.id, duration)

    def execute(self):
        self.execute_script(self.script, self.devices)

    def summary(self):
        summary.show_summary()
        oriole.dump()

    def run(self, args):
        t1 = perf_counter()
        if args.check:
            return
        self.setup_devices()
        t2 = perf_counter()
        try:
            self.execute()
        except GeneralException:
            logger.exception("Task Execution Failure...")
        except KeyboardInterrupt:
            logger.exception("Task Execution Interrupted(CTRL+C received)...")
        finally:
            t3 = perf_counter()
            if args.submit_flag != "none":
                oriole.submit()
            self.summary()
            t4 = perf_counter()
            logger.debug("Setting up devices takes %.1f s", t2 - t1)
            logger.debug("Executing testcases takes %.1f s", t3 - t2)
            logger.debug("Generating summary report takes %.1f s", t4 - t3)
