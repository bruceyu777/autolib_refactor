import argparse
import os
import sys


def get_ubuntu_version_number():
    version = "1804"
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("VERSION_ID="):
                    print(f"Your OS version is {line}")
                    version = (
                        line.split("=", 1)[1]
                        .strip()
                        .strip('"')
                        .strip("'")
                        .replace(".", "")
                    )
    except (OSError, ValueError):
        print("Unable to read Ubuntu version from /etc/os-release file.")
    print(f"Ubuntu version will be used: {version}")
    return version


class Upgrade(argparse.Action):
    default_binary_filename = "autotest"
    binary_root_dir = "http://172.18.52.254/AutoLib/"

    def __init__(self, option_strings, dest, nargs=0, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)
        self.kwargs = kwargs

    def get_binary_filename(self):
        version = int(get_ubuntu_version_number())
        if version < 1804:
            raise RuntimeError(
                "Autolib and Upgrade is only available for Ubuntu 18.04 and above."
            )
        selected = "autotest_1804" if version == 1804 else "autotest_2004"
        print(f"Selected binary is: {selected}")
        return selected

    def __call__(self, parser, namespace, values, option_string=None):
        self._upgrade()

    def _upgrade(self):
        # Create a pipe for communication between parent and child processes
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid > 0:
            self._parent_process(read_fd, write_fd)
        else:
            self._child_process(write_fd)

    def _parent_process(self, read_fd, write_fd):
        os.close(write_fd)
        with os.fdopen(read_fd) as read_pipe:
            while True:
                line = read_pipe.readline()
                if not line:
                    break
                print(line, end="")
                sys.stdout.flush()
        sys.exit(0)

    def _child_process(self, write_fd):
        self._close_unused_fds(write_fd)
        with os.fdopen(write_fd, "w") as write_pipe:
            write_pipe.write("Started to upgrade.\n")
            if self._upgrade_logic():
                write_pipe.write("Succeeded to upgrade.\n")
            else:
                write_pipe.write("Failed to upgrade.\n")
        sys.exit(0)

    def _close_unused_fds(self, write_fd):
        max_fd = os.sysconf("SC_OPEN_MAX") if hasattr(os, "sysconf") else 2048
        for fd in range(3, max_fd):
            if fd == write_fd:
                continue
            try:
                os.close(fd)
            except OSError:
                pass

    def _upgrade_logic(self):
        os.system(f"rm -rf {self.default_binary_filename}")
        binary_filename = self.get_binary_filename()
        release_on_server = f"{self.binary_root_dir}{binary_filename}"
        exit_status = os.system(f"curl -O {release_on_server}")
        os.system(f"mv {binary_filename} {self.default_binary_filename}")
        os.system(f"chmod +x {self.default_binary_filename}")
        return exit_status == 0
