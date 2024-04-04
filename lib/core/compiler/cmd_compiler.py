import os
import re
from pathlib import Path

from .vm_code import VMCode

VM_CODES_PATH = Path(__file__).resolve().parent / "vm_codes"


class VmCodesParser:
    def __init__(self, folder_path=VM_CODES_PATH):
        self.folder_path = folder_path

    def run(self):
        all_codes = {}
        files = os.listdir(self.folder_path)
        for file_name in files:
            file_path = self.folder_path / file_name
            if os.path.isfile(file_path):
                vm_codes = []
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        codes = line.split(",")
                        new_codes = []
                        for code in codes:
                            code = code.strip()
                            if code.isdigit():
                                new_codes.append(int(code))
                            else:
                                new_codes.append(code)
                        codes = new_codes
                        operation = codes[0]
                        parameters = codes[1:] if len(codes) > 1 else ()
                        vm_codes.append((operation, parameters))
                all_codes[file_path.stem] = vm_codes
        return all_codes


class CmdCompiler:
    def __init__(self):
        self.codes = VmCodesParser().run()

    def _is_reset_command(self, command):
        pattern = re.compile(
            r"(exe.*factoryreset.*|exe.*forticarrier-license|resetFirewall)"
        )
        return re.match(pattern, command)

    def _is_restore_command(self, command):
        return re.match("exe.*restore.*|exe.*vm-license(\s.*)?$", command)

    def _is_reboot_command(self, command):
        return re.match("exe.*reboot.*", command)

    def _is_restore_ips_command(self, command):
        return re.match("exe.*restore.*ips", command)

    def _is_purge_command(self, command):
        return re.match("purge", command)

    def compile(self, command, line_number):
        vm_codes = []
        if self._is_reset_command(command):
            if command == "resetFirewall":
                command = "exe factoryreset"
                vm_codes = [
                    VMCode(line_number, "send_line", ("config global",)),
                    VMCode(line_number, "send_line", (command,)),
                ]
                vm_codes = vm_codes + [
                    VMCode(line_number, operation, parameters)
                    for operation, parameters in self.codes["reset_firewall"]
                ]
            else:
                vm_codes = [VMCode(line_number, "send_line", (command,))]
                vm_codes = vm_codes + [
                    VMCode(line_number, operation, parameters)
                    for operation, parameters in self.codes["reset_command"]
                ]
            return vm_codes
        if self._is_restore_ips_command(command):
            vm_codes = [VMCode(line_number, "send_line", (command,))]
            vm_codes = vm_codes + [
                VMCode(line_number, operation, parameters)
                for operation, parameters in self.codes["restore_ips_command"]
            ]
            return vm_codes
        if self._is_restore_command(command):
            vm_codes = [VMCode(line_number, "send_line", (command,))]
            vm_codes = vm_codes + [
                VMCode(line_number, operation, parameters)
                for operation, parameters in self.codes["restore_command"]
            ]
            return vm_codes
        # if self._is_purge_command(command):
        #     vm_codes = [VMCode(line_number, "send_line", (command,))]
        #     vm_codes = vm_codes + [
        #         VMCode(line_number, operation, parameters)
        #         for operation, parameters in self.codes["purge_command"]
        #     ]
        #     return vm_codes
        if self._is_reboot_command(command):
            vm_codes = [VMCode(line_number, "send_line", (command,))]
            vm_codes = vm_codes + [
                VMCode(line_number, operation, parameters)
                for operation, parameters in self.codes["reboot_command"]
            ]
            return vm_codes
        return [VMCode(line_number, "command", (command,))]
