from .fos_dev import FosDev


class FortiGate(FosDev):
    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        return self.model.replace("-", "_").replace("FortiGate", "FGT")


    @property
    def system_status(self):
        rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*?"
            r"Serial-Number: (?P<serial>[^\r\n]*).*?"
            r"BIOS version: (?P<bios_version>[^\r\n]*).*?"
            r"Virtual domain configuration: (?P<vdom_mode>[^\r\n]*).*?"
            r"Branch point: (?P<branch_point>[^\r\n]*).*?"
        )
        matched = self.show_command_may_have_more("get system status", rule)
        if not matched:
            rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
            r"Serial-Number: (?P<serial>[^\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
            r"Branch point: (?P<branch_point>[^\n]*).*"
        )
            matched = self.show_command_may_have_more("get system status", rule)
        return matched
