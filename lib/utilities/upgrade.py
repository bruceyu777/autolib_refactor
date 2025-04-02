import argparse
import os
import sys


class Upgrade(argparse.Action):
    def __init__(self, option_strings, dest, nargs=0, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)
        self.binary_filename = kwargs.get("binary_filename", "autotest")
        self.release_on_server = kwargs.get(
            "release_on_server", f"http://172.18.52.254/AutoLib/{self.binary_filename}"
        )

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
        os.system(f"rm -rf {self.binary_filename}")
        exit_status = os.system(f"curl -O {self.release_on_server}")
        return exit_status == 0
