import fcntl
import os
import sys

from lib.services import output


class MultiIO:
    def __init__(self, *fds):
        self.fds = fds
        self.pause_write_stdout = False

    def write(self, data):
        for fd in self.fds:
            if fd == sys.stdout and self.pause_write_stdout:
                continue
            fd.write(data)

    def flush(self):
        for fd in self.fds:
            fd.flush()

    def pause_stdout(self):
        self.pause_write_stdout = True

    def resume_stdout(self):
        self.pause_write_stdout = False


# pylint : disable = consider-using-with
class LogFile:
    FILE_TABLE = {
        "read": "logfile_read",
        "send": "logfile_send",
        "interaction": "logfile",
    }

    def __init__(self, client, dev_name):
        self.client = client
        self.dev_name = dev_name
        self.fps = []

    def start_record(self, folder_name):
        for log_type, log_file in self.FILE_TABLE.items():
            file_name = f"{self.dev_name}_{log_type}.txt"
            file_path = output.compose_terminal_file(folder_name, file_name)
            # pylint: disable=consider-using-with
            fp = open(file_path, "a", encoding="utf-8")

            flags = fcntl.fcntl(fp, fcntl.F_GETFL)  # Get current file flags
            flags &= ~os.O_NONBLOCK  # Clear the O_NONBLOCK flag
            fcntl.fcntl(fp, fcntl.F_SETFL, flags)  # Set the new flags

            if log_type == "interaction":
                interaction_fps = MultiIO(fp, sys.stdout)
                setattr(self.client, log_file, interaction_fps)
            else:
                setattr(self.client, log_file, fp)
            self.fps.append(fp)

    def stop_record(self):
        for fp in self.fps:
            fp.close()

    def pause_stdout(self):
        self.client.logfile.pause_stdout()

    def resume_stdout(self):
        self.client.logfile.resume_stdout()
