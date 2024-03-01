from lib.services import output
import sys

class MultiIO:
    def __init__(self, *fds):
        self.fds = fds

    def write(self, data):
        for fd in self.fds:
            fd.write(data)

    def flush(self):
        for fd in self.fds:
            fd.flush()

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
        fps = []
        for log_type, log_file in self.FILE_TABLE.items():
            file_name = f"{self.dev_name}_{log_type}.log"
            file_path = output.compose_terminal_file(folder_name, file_name)
            fp = open(file_path, "a", encoding="utf-8")
            if log_type == "interaction":
                interaction_fps = MultiIO(fp, sys.stdout)
                self.client.__setattr__(log_file, interaction_fps)
            else:
                self.client.__setattr__(log_file, fp)
            self.fps.append(fp)

    def stop_record(self):
        for fp in self.fps:
            fp.close()



