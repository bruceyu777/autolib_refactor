import re
from lib.services.output import output

ERROR_INFO = ("Unknown action", "command parse error", "Command fail", "incomplete command", "no tablename", "no object", "value parse error", "ambiguous command",
"internal error", "discard the setting", "not found in table", "unset oper error ret", "Attribute(.*?)Must be set", "not found in datasource",
"object set operator error", "node_check_object fail", "object check operator error", "value invalid", "invalid netmask",
"invalid integer value", "invalid unsigned integer value", "invalid input", "duplicated with another vip",
)
FAILED_COMMANDS_FILE_NAME = "failed_commands.txt"


class CmdExecChecker:
    def __init__(self, script, line_number, command, result):
        self.script = script
        self.line_number = line_number
        self.command = command
        self.result = result
        self.failed_commands_file_name = output.compose_summary_file(
            FAILED_COMMANDS_FILE_NAME
        )

    def check(self):
        failed_pattern = "|".join(ERROR_INFO)
        m = re.search(failed_pattern, self.result)
        if m:
            error = m.group()
            self.dump_failed_commands(error)

    def dump_failed_commands(self, error):
        with open(
            self.failed_commands_file_name, "a", encoding="utf-8"
        ) as f:
            f.write(f"Command: {self.script}:{self.line_number} {self.command} Error: {error}\n")

if __name__ == "__main__":
    pass

