class AutoTestException(Exception):
    def __init__(self, value):
        super().__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)


class CompileException(AutoTestException):
    def __init__(self, file_name, line_number, expected, current):
        self.message = f"Error: {file_name}:{line_number}, expect {expected}, but current is {current}."
        super().__init__(self.message)


class ParseException(AutoTestException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnSpecifiedRelease(AutoTestException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnSpecifiedBuild(AutoTestException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnSupportedModel(AutoTestException):
    def __init__(self, model):
        self.message = f"Model {model} is not supported!"
        super().__init__(self.message)


class OperationFailure(AutoTestException):
    """for KVM operations"""

    def __init__(self, value):
        self.message = "Operation Failure: %s!" % value
        super().__init__(self.message)


class ImageNotFound(AutoTestException):
    def __init__(self, image):
        self.message = "Image %s not found!" % image
        super().__init__(self.message)


class DeviceCfgNotFound(AutoTestException):
    def __init__(self, dev_name):
        self.message = "Device config for %s not found!" % dev_name
        super().__init__(self.message)


class LoginDeviceFailed(AutoTestException):
    def __init__(self, dev_name):
        self.message = "Could not login device %s!" % dev_name
        super().__init__(self.message)


class ImageDownloadErr(AutoTestException):
    def __init__(self, image):
        self.message = "Image %s download failed!" % image
        super().__init__(self.message)


class ResourceNotAvailable(AutoTestException):
    def __init__(self, value):
        self.message = "Resource is NOT avaiable: %s!!" % value
        super().__init__(self.message)


class KernelPanicErr(AutoTestException):
    def __init__(self, value):
        self.message = "Kernel panic: %s!!" % value
        super().__init__(self.message)


class RestoreFailure(AutoTestException):
    def __init__(self, device, release, build):
        self.message = "Restore failure: %s %s %s!!" % device, release, build
        super().__init__(self.message)


class NotSupportedDevice(AutoTestException):
    def __init__(self, device):
        self.message = "Not supported device: %s!!" % device
        super().__init__(self.message)


class VariableNotFound(AutoTestException):
    def __init__(self, variable):
        self.message = "variable not found: %s!!" % variable
        super().__init__(self.message)


class FileNotExist(AutoTestException):
    def __init__(self, file):
        self.message = "File: %s does not exist!!" % file
        super().__init__(self.message)


class ItemNotDefined(AutoTestException):
    def __init__(self, item):
        self.message = "Item: %s is not defined!!" % item
        super().__init__(self.message)

class SyntaxError(AutoTestException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class LicenseLoadErr(AutoTestException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class ReportUnderPCWithoutDut(AutoTestException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)