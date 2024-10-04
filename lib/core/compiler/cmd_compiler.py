import json
import os
import re
from pathlib import Path

from .vm_code import VMCode

VM_CODES_PATH = Path(__file__).resolve().parent / "vm_codes"


class VmCodesParser:
    vm_code_suffix = ".vm"

    def __init__(self, folder_path=VM_CODES_PATH):
        self.folder_path = folder_path

    def _extract_operation_and_parameters(self, line):
        stripped_parts = (p.strip() for p in line.split(","))
        codes = [int(code) if code.isdigit() else code for code in stripped_parts]
        operation, *parameters = codes
        return operation, parameters

    def _load_vm_codes_from_file(self, file_path):
        vm_codes = []
        with open(file_path, "r", encoding="utf-8") as f:
            vm_codes = [self._extract_operation_and_parameters(line) for line in f]
        return vm_codes

    @staticmethod
    def is_vmcode_file(file_path):
        return file_path.suffix == VmCodesParser.vm_code_suffix

    def _vm_code_files(self):
        for root, _, files in os.walk(self.folder_path):
            for filename in files:
                filepath = self.folder_path / root / filename
                if self.is_vmcode_file(filepath):
                    yield filepath

    def run(self):
        return {
            file_path.stem: self._load_vm_codes_from_file(file_path)
            for file_path in self._vm_code_files()
        }


class CmdCompiler:
    def __init__(self):
        self.codes = VmCodesParser().run()

    def _is_reset_command(self, command):
        pattern = re.compile(
            r"(exe.*factoryreset.*|exe.*forticarrier-license|resetFirewall)"
        )
        return re.match(pattern, command)

    def _is_restore_command(self, command):
        return re.match(r"exe.*restore.*|exe.*vm-license(\s.*)?$", command)

    def _is_reboot_command(self, command):
        return re.match("exe.*reboot.*", command) or command == "rebootFirewall"

    def _is_restore_ips_command(self, command):
        return re.match("exe.*restore.*ips", command)

    def _is_purge_command(self, command):
        return re.match("purge", command)

    def _generate_reboot_command_vm_codes(self, command, line_number):
        if command == "rebootFirewall":
            vm_codes = [
                VMCode(line_number, "send_line", ("config global",)),
                VMCode(line_number, "send_line", ("exe reboot",)),
            ]
        else:
            vm_codes = [VMCode(line_number, "send_line", (command,))]
        vm_codes = vm_codes + [
            VMCode(line_number, operation, parameters)
            for operation, parameters in self.codes["reboot_command"]
        ]
        return vm_codes

    def _generate_restore_command_vm_codes(self, command, line_number):
        vm_codes = [VMCode(line_number, "send_line", (command,))] + [
            VMCode(line_number, operation, parameters)
            for operation, parameters in self.codes["restore_command"]
        ]
        return vm_codes

    def _generate_restore_ips_command_vm_codes(self, command, line_number):
        vm_codes = [VMCode(line_number, "send_line", (command,))] + [
            VMCode(line_number, operation, parameters)
            for operation, parameters in self.codes["restore_ips_command"]
        ]
        return vm_codes

    def compile(self, command, line_number):
        if self._is_restore_ips_command(command):
            return self._generate_restore_ips_command_vm_codes(command, line_number)
        if self._is_restore_command(command) and not command.startswith(
            "exe restore script"
        ):
            return self._generate_restore_command_vm_codes(command, line_number)
        if self._is_reboot_command(command):
            return self._generate_reboot_command_vm_codes(command, line_number)
        return [VMCode(line_number, "command", (command,))]


if __name__ == "__main__":
    compiler = CmdCompiler()
    compiled_codes = compiler.codes
    print(json.dumps(compiled_codes, indent=4))
    assert "reset_firewall" in compiled_codes
    assert compiled_codes["restore_vm_license_command"] == []
