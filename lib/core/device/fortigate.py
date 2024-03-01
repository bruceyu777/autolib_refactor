from .fos_dev import FosDev


class FortiGate(FosDev):
    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        return self.model.replace("-", "_").replace("FortiGate", "FGT")
