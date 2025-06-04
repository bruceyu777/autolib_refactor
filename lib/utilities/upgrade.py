import os
import re
import shutil
import subprocess
import sys
import urllib


def get_linux_version():
    try:
        result = subprocess.run(
            ["cat", "/etc/lsb-release"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True,
        )
        print(f"Your Linux Information: \n{result.stdout}")

        matched = re.search(r"DISTRIB_RELEASE=([\d.]+)", result.stdout)
        if matched:
            version = matched.group(1)
            return version.replace(".", "")
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'cat /etc/lsb-release': {e}")
        print(f"Stderr: {e.stderr.strip()}")
    except Exception as e:
        print(f"An unexpected error occurred while detecting Linux version: {e}")

    return "1804"


class Upgrade:
    default_binary_filename = "autotest"
    backup_binary_filename = ".autotest.original"
    temp_binary_filename = ".autotest.downloaded.temp"
    binary_root_url = "http://172.18.52.254/AutoLib"

    def __init__(self, build=None, branch="V3R10"):
        self.build = build
        self.branch = branch

    def get_binary_filename(self):
        version_str = get_linux_version()
        try:
            version = int(version_str)
        except ValueError:
            print(
                f"Warning: Could not parse Linux version '{version_str}'. Defaulting to '1804'."
            )
            version = 1804
        if version < 1804:
            raise RuntimeError(
                "Autolib Binaary does not support Ubuntu Version below 18.04."
            )
        selected = "autotest_1804" if version == 1804 else "autotest_2004"
        print(f"Selected binary is: {selected}")
        return selected

    def run(self):
        print("***** Started to Upgrade Autotest Binary ******")
        is_success = self._upgrade_logic()
        print(f"***** Upgrade Status: {'Succeeded' if is_success else 'Failed'} ******")
        sys.exit(0 if is_success else 1)

    def _download_binary(self, url):
        print(f"Downloading update from: {url}")
        try:
            urllib.request.urlretrieve(url, self.temp_binary_filename)
            print("Download completed successfully.")
            return True
        except Exception as e:
            print(f"An unexpected error occurred during download: {e}")
            return False

    def _backup_current_binary(self):
        print(f"Backing up current binary to {self.backup_binary_filename}...")
        try:
            shutil.move(self.default_binary_filename, self.backup_binary_filename)
            print("Backup successful.")
            return True
        except Exception as e:
            print(f"An unexpected error occurred during backup: {e}")
            return False

    def _replace_binary(self):
        print(
            f"Moving new binary from '{self.temp_binary_filename}' to '{self.default_binary_filename}' ..."
        )
        try:
            shutil.move(self.temp_binary_filename, self.default_binary_filename)
            os.chmod(self.default_binary_filename, 0o755)
            print(
                f"New binary successfully moved to '{self.default_binary_filename}' and permissions set."
            )
            return True
        except (shutil.Error, OSError, Exception) as e:
            print(f"An unexpected error occurred during binary replacement: {e}")
            return False

    def _cleanup_backup(self):
        if os.path.exists(self.backup_binary_filename):
            print(f"Removing old backup binary '{self.backup_binary_filename}' ...")
            try:
                os.remove(self.backup_binary_filename)
                print("Old backup removed.")
                return True
            except Exception as e:
                print(f"An unexpected error occurred during backup cleanup: {e}")
                return False
        return True

    def _revert_to_backup(self):
        if os.path.exists(self.temp_binary_filename):
            try:
                os.remove(self.temp_binary_filename)
            except Exception as e:
                print(f"Error removing temp file '{self.temp_binary_filename}': {e}")

        if not os.path.exists(self.backup_binary_filename):
            print(f"Backup file '{self.backup_binary_filename}' does not exist.")
            return False

        try:
            shutil.move(self.backup_binary_filename, self.default_binary_filename)
            print(
                f"Reverted {self.default_binary_filename} to backup '{self.backup_binary_filename}'."
            )
            return True
        except Exception as e:
            print(f"Error reverting to backup: {e}")
            return False

    def _get_target_url(self):
        binary_filename = self.get_binary_filename()
        if self.build is None:
            return f"{self.binary_root_url}/{binary_filename}"
        return f"{self.binary_root_url}/{self.branch}/{self.build}/{binary_filename}"

    def _upgrade_logic(self):

        remote_url = self._get_target_url()
        if not self._download_binary(remote_url):
            return False

        self._backup_current_binary()

        if not self._replace_binary():
            self._revert_to_backup()
            return False

        self._cleanup_backup()

        return True
