import sys
from enum import IntEnum


class DebugStatus(IntEnum):
    OFF = 0
    ON = 1


class DebugAction(IntEnum):
    EXECUTE = 0
    WAIT_FOR_INPUT = 1


LIST_HELP_MSG = """List source code for the current file, line numbers is sepcified by count.
list 3, will list the current line and the other two lines following the current line,
list -3, will list the current line and the other two lines before the current line."""
COMMANDS = [
    (
        "s(tep)",
        (
            "Step to next command(for wrappers that involve more than one "
            "commands, it will go to the next command in the wrapper)."
        ),
    ),
    ("c(ontinue)", "Continue execution, only stop when a breakpoint is encountered."),
    ("j(ump) <lineno>", "Jump to specified line number."),
    ("q(uit)", "Quit from the debugger. The program being executed is aborted."),
    ("l(ist) <count>", LIST_HELP_MSG),
    ("h(elp)", ""),
]


ABBRS = {command[0].split("(", maxsplit=1)[0]: command for command in COMMANDS}


class Debugger:
    def __init__(self, lines, vm_codes, mode=DebugStatus.OFF):
        self.mode = mode
        self.lines = lines
        self.line_number = None
        self.program_counter = None  # abbreviated as"pc"
        self.vm_codes = vm_codes
        self.next_pc = None
        self.next_action = None

    def breakpoint(self):
        self.mode = DebugStatus.ON

    def _step(self, _):
        self.next_pc = self.program_counter
        self.next_action = DebugAction.EXECUTE

    def _continue(self, _):
        self.mode = DebugStatus.OFF
        self.next_pc = self.program_counter
        self.next_action = DebugAction.EXECUTE

    def _quit(self, _):
        sys.exit(0)

    def _jump(self, line_number):
        if line_number <= 0 or line_number > len(self.lines):
            print("Invalid line number.")
            self.next_action = DebugAction.WAIT_FOR_INPUT
            return
        for index, vm_code in enumerate(self.vm_codes):
            if line_number == vm_code.line_number:
                self.next_pc = index
                self.next_action = DebugAction.EXECUTE
                return
        print("Invalid line number.")
        self.next_action = DebugAction.WAIT_FOR_INPUT
        return

    def _list(self, count):
        if count > 0:
            for i in range(count):
                if self.line_number + i - 1 < len(self.lines):
                    print(
                        f"{self.line_number + i} {self.lines[self.line_number + i - 1]}"
                    )
        else:
            for i in range(count, 1):
                if self.line_number + i - 1 >= 0:
                    print(
                        f"{self.line_number + i} {self.lines[self.line_number + i - 1]}"
                    )
        self.next_action = DebugAction.WAIT_FOR_INPUT

    def _expect_input(self):
        for command in COMMANDS[:-1]:
            print(f"{command[0]:{20}}: {command[1]}")

    def _help(self, _):
        self._expect_input()
        self.next_action = DebugAction.WAIT_FOR_INPUT

    def _parse_input(self, user_input):
        tokens = user_input.strip().split()
        if len(tokens) not in [1, 2]:
            self._expect_input()
            return None, None
        action = tokens[0]
        if len(action) == 1:
            if action not in ABBRS:
                self._expect_input()
                return None, None
            action = ABBRS[action][0].replace("(", "").replace(")", "").split()[0]

        if len(tokens) == 1:
            if action not in ["step", "continue", "quit", "help"]:
                self._expect_input()
                return None, None
            return action, None
        para = int(tokens[1])
        if action not in ["jump", "list"]:
            self._expect_input()
            return None, None

        return action, para

    def run(self, line_number, program_counter):
        if self.mode is DebugStatus.OFF:
            return program_counter
        self.line_number = line_number
        self.program_counter = program_counter
        print(f"{self.line_number} {self.lines[self.line_number - 1]}")
        while True:
            user_input = input("(debug):")
            action, para = self._parse_input(user_input)
            if action is None:
                continue
            func = getattr(self, f"_{action}")
            func(para)
            if self.next_action is DebugAction.EXECUTE:
                break
        return self.next_pc


if __name__ == "__main__":
    test_lines = ["helle", "word", "next", "end"]
    parsed_codes = []
    pc = 0
    dbg = Debugger(test_lines, parsed_codes)
    dbg.breakpoint()
    pc = dbg.run(0, 0)

    print(pc)
