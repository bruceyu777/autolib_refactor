from .fos_dev import FosDev


class FortiVM(FosDev):
    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        image_prefix = (
            self.model.replace("-", "_")
            .replace("FortiGate", "FGT")
            .replace("FortiCarrier", "FGT")
        )
        return image_prefix.replace("-", "_").replace("FortiFirewall", "FFW")

    @property
    def system_status(self):
        rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
            r"Serial-Number: (?P<serial>[^\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
            r"Branch point: (?P<branch_point>[^\n]*).*"
        )
        result, m, _ = self.send_command("get system status", rule, timeout=10)
        return m.groupdict() if m and result else {}
