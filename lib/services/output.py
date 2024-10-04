import os
import zipfile
from datetime import datetime

from lib.settings import OUTPUTS_DIR

TERMINAL = "terminal"
COMPILED = "compiled"
SUMMARY = "summary"
LOGS = "logs"


class Output:
    def __init__(self):
        current_date = str(datetime.now().date())
        current_time = datetime.now().time().strftime("%H-%M-%S")
        self.directory_path = OUTPUTS_DIR / current_date / current_time

    @staticmethod
    def _compose_folder(parent_folder, folder_name):
        folder = parent_folder / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def compose_terminal_file(self, folder_name, file_name):
        return self._compose_file(folder_name, TERMINAL, file_name)

    def compose_compiled_file(self, folder_name, file_name):
        return self._compose_file(folder_name, COMPILED, file_name)

    def compose_summary_file(self, file_name):
        folder = self._compose_folder(self.directory_path, SUMMARY)
        return folder / file_name

    def compose_log_file(self, folder_name, file_name):
        return self._compose_file(folder_name, LOGS, file_name)

    def _compose_file(self, folder_name, file_type, file_name):
        parent_folder = self.directory_path / folder_name
        return self._compose_folder(parent_folder, file_type) / file_name

    def get_current_output_dir(self):
        return "/".join(self.directory_path.parts[-3:])

    def zip_autotest_log(self):
        zip_file = self.compose_summary_file("autotest.zip")
        log_file = self.compose_summary_file("autotest.log")
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(log_file, arcname=os.path.basename(log_file))
        os.remove(log_file)


output = Output()
