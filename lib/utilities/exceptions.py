class GeneralException(Exception):
    def __init__(self, value):
        super().__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)


class BlockingException(Exception):
    def __init__(self, value):
        super().__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)


class CompileException(GeneralException):
    def __init__(self, file_name, line_number, expected, current):
        self.message = f"Error: {file_name}:{line_number}, expect {expected}, but current is {current}."
        super().__init__(self.message)


class ParseException(GeneralException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnSupportedModel(BlockingException):
    def __init__(self, model):
        self.message = f"Model {model} is not supported!"
        super().__init__(self.message)


class OperationFailure(BlockingException):

    def __init__(self, value):
        self.message = "Operation Failure: %s!" % value
        super().__init__(self.message)


class ImageNotFound(BlockingException):
    def __init__(self, image):
        self.message = "Image %s not found!" % image
        super().__init__(self.message)


class LoginDeviceFailed(GeneralException):
    def __init__(self, dev_name):
        self.message = "Could not login device %s!" % dev_name
        super().__init__(self.message)


class ImageDownloadErr(BlockingException):
    def __init__(self, image):
        self.message = "Image %s download failed!" % image
        super().__init__(self.message)


class ResourceNotAvailable(BlockingException):
    def __init__(self, value):
        self.message = "Resource is NOT avaiable: %s!!" % value
        super().__init__(self.message)


class KernelPanicErr(BlockingException):
    def __init__(self, value):
        self.message = "Kernel panic: %s!!" % value
        super().__init__(self.message)


class RestoreFailure(GeneralException):
    def __init__(self, device, release, build):
        self.message = "Restore failure: %s %s %s!!" % device, release, build
        super().__init__(self.message)


class NotSupportedDevice(GeneralException):
    def __init__(self, device):
        self.message = "Not supported device: %s!!" % device
        super().__init__(self.message)


class VariableNotFound(GeneralException):
    def __init__(self, variable):
        self.message = "variable not found: %s!!" % variable
        super().__init__(self.message)


class FileNotExist(BlockingException):
    def __init__(self, file):
        self.message = "File: %s does not exist!!" % file
        super().__init__(self.message)


class ScriptSyntaxError(GeneralException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class LicenseLoadErr(GeneralException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class ReportUnderPCWithoutDut(GeneralException):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
