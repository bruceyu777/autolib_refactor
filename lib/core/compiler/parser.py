from pathlib import Path

from lib.services import logger, output, summary
from lib.utilities.exceptions import ScriptSyntaxError

from .syntax import script_syntax
from .vm_code import VMCode


class Parser:
    def __init__(self, file_name, tokens, lines):
        self.tokens = tokens
        self.cursor = 0
        self.vm_codes = []
        self.file_name = file_name
        self.lines = lines
        self.cur_line_number = 0
        self.devices = set()
        self.called_files = set()
        self.cur_section = None

    @property
    def _cur_token(self):
        if self.cursor < len(self.tokens):
            return self.tokens[self.cursor]
        return None

    def _advance(self):
        self.cursor += 1

    def _retreat(self):
        self.cursor -= 1

    def _add_vm_code(self, line_number, operation, parameters):
        if operation == "report":
            summary.add_testcase(parameters[0])
        vm_code = VMCode(line_number, operation, parameters)
        self.vm_codes.append(vm_code)
        return vm_code

    def run(self):
        while self._cur_token is not None:
            self._script()
        self.dump_vm_codes()
        return self.vm_codes, self.devices, self.called_files

    def _script(self):
        token = self._cur_token
        if not script_syntax.is_valid_script_type(token.type):
            self._raise_syntax_error(
                f"Unexpected token type '{token.type}' for '{token.str}'"
            )
        if script_syntax.at_top_level_category(token.type):
            syntax_definition = script_syntax.get_token_syntax_definition(token)
            if syntax_definition is None:
                self._raise_syntax_error(
                    f"Unexpected token '{token.str}'",
                )

            operation, matched_rule = syntax_definition
            getattr(self, f"_{operation}")(matched_rule)
        else:
            func = self._get_func_handler()
            func()
            self._advance()

    def _comment(self):
        token = self._cur_token
        self._add_vm_code(token.line_number, "comment", (token.str,))

    def _section(self):
        token = self._cur_token
        self._add_vm_code(token.line_number, "switch_device", (token.str,))
        self.cur_section = token.str
        self.devices.add(token.str)

    def _command(self):
        token = self._cur_token
        cmd_vm_codes = [VMCode(token.line_number, "command", (token.str,))]
        if self.cur_section is not None and self.cur_section.startswith(("FGT", "FVM")):
            if not script_syntax.is_valid_command(token.str.strip()):
                logger.debug(
                    "Warning, unknown or incompleted command %s:%d: %s",
                    self.file_name,
                    token.line_number,
                    token.str,
                )
        self.vm_codes.extend(cmd_vm_codes)

    def _include(self):
        token = self._cur_token
        self._add_vm_code(token.line_number, "include", (token.str,))
        self.called_files.add((token.str, self.cur_section))

    def _parse_token(self, expected_type=None, expected_str=None):
        token = self._cur_token
        if token is None:
            return None
        if token.line_number != self.cur_line_number:
            self._retreat()
            if expected_str:
                self._raise_syntax_error(
                    f"Unexpected token '{token.str}' expected {expected_str}.",
                )
            if expected_type:
                self._raise_syntax_error(
                    f"Unexpected token '{token.str}' expected token type of '{expected_type}'.",
                )
            return None
        token_str = token.str
        token_type = token.type
        if expected_str:
            if token_str != expected_str and token_str not in expected_str:
                self._raise_syntax_error(
                    f"Unexpected token '{token_str}' expected {expected_str}.",
                )
        if expected_type:
            if token_type != expected_type and token_type not in expected_type:
                self._raise_syntax_error(
                    f"Unexpected token type '{token_type}' expected {expected_type}.",
                )

        self._advance()
        return token

    def _extract(self, expected_tokens):
        all_tokens = []
        for expected_token in expected_tokens:
            expected_type, expected_str = expected_token
            token = self._parse_token(expected_type, expected_str)
            if expected_str is None:
                all_tokens.append(token)
        return all_tokens

    def _parse(self, expected_tokens):
        cur_token = self._cur_token
        self.cur_line_number = cur_token.line_number
        self._advance()
        tokens = ()
        if expected_tokens:
            tokens = self._extract(expected_tokens)
        parameters = [token.str for token in tokens if token is not None]
        self._add_vm_code(cur_token.line_number, cur_token.str, parameters)

    def _get_func_handler(self, refer="type"):
        token = self._cur_token
        base_name = token.type if refer == "type" else token.str
        func = getattr(self, f"_{base_name}")
        if not func:
            self._raise_syntax_error(f"Unsupported {token.type} {token.str}.")
        return func

    def _term(self):
        token = self._cur_token
        if token.type in {"variable", "identifier", "number"}:
            self._parse_token()
        return token

    def _expression(self):
        self.cur_line_number = self._cur_token.line_number
        expression_tokens = []
        token = self._term()
        expression_tokens.append(token.str)

        token = self._cur_token
        while token is not None and token.type in ["operator", "symbol"]:
            token = self._parse_token()
            expression_tokens.append(token.str)
            token = self._term()
            expression_tokens.append(token.str)
            token = self._cur_token

        return expression_tokens

    def _is_ctrl_blk_end(self, cur_block_end):
        return (
            self._cur_token.type == "keyword" and self._cur_token.str in cur_block_end
        )

    def _eof(self):
        return self.cursor == len(self.tokens)

    def _control_block(self, exp_stats, prev_code=None):
        func = self._get_func_handler("str")
        vm_code = func(prev_code)
        self._advance()
        if not exp_stats:
            return
        cur_block_end = exp_stats[-1]

        for exp_stat in exp_stats:
            if exp_stat == "expression":
                expression_tokens = self._expression()
                for s in expression_tokens:
                    vm_code.add_parameter(s)
            elif exp_stat == "script":
                while not self._eof() and not self._is_ctrl_blk_end(cur_block_end):
                    self._script()
            else:
                if self._eof():
                    self._raise_syntax_error(
                        f"Unexpected EOF, missed {cur_block_end}.",
                    )
                exp_stats = script_syntax.get_keyword_cli_syntax(self._cur_token.str)
                self._control_block(exp_stats, vm_code)

    def _parse_options(self, matched_rule):
        options_default, option_rule = matched_rule
        options = options_default.copy()
        command_token = self._cur_token
        self._advance()
        token = self._cur_token
        while token and token.str.startswith("-") and token.type == "identifier":
            option = token.str
            self.cur_line_number = command_token.line_number
            tokens = self._extract(option_rule)
            if len(tokens) != 2:
                self._raise_syntax_error(
                    f"Failed to parse value for '{option}'",
                )
            value = tokens[1]
            if value is None:
                self._raise_syntax_error(f"Failed to parse value for '{option}'")
            if value.line_number != command_token.line_number:
                self._retreat()
                self._raise_syntax_error(f"Failed to parse value for '{option}'")
            if option == "-fail":
                if value.str.startswith("-"):
                    self._retreat()
                    options["-fail"] = "unmatch"

            options[option] = value.str
            token = self._cur_token
        self._add_vm_code(
            command_token.line_number,
            command_token.str,
            [options[k] for k in options],
        )

    def _if(self, _):
        return self._add_vm_code(self._cur_token.line_number, "if_not_goto", ())

    def _elseif(self, prev_vm_code):
        prev_vm_code.add_parameter(self._cur_token.line_number)
        return self._add_vm_code(self._cur_token.line_number, "elseif", ())

    def _else(self, prev_vm_code):
        if prev_vm_code is None:
            self._raise_syntax_error(
                f"else without if {self.file_name}:{self._cur_token.line_number}"
            )
        prev_vm_code.add_parameter(self._cur_token.line_number)
        return self._add_vm_code(self._cur_token.line_number, "else", ())

    def _fi(self, prev_vm_code):
        if prev_vm_code is None:
            self._raise_syntax_error("fi without if")
        prev_vm_code.add_parameter(self._cur_token.line_number)
        return self._add_vm_code(self._cur_token.line_number, "endif", ())

    def _loop(self, _):
        return self._add_vm_code(self._cur_token.line_number, "loop", ())

    def _intchange(self, _):
        return self._add_vm_code(self._cur_token.line_number, "intchange", ())

    def _until(self, prev_vm_code):
        return self._add_vm_code(
            self._cur_token.line_number, "until", (prev_vm_code.line_number,)
        )

    def _while(self, _):
        return self._add_vm_code(self._cur_token.line_number, "loop", ())

    def _endwhile(self, prev_vm_code):
        return self._add_vm_code(
            self._cur_token.line_number, "until", (prev_vm_code.line_number,)
        )

    def _raise_syntax_error(self, err_msg):
        token = self._cur_token
        if token is None:
            token = self.tokens[-1]
        raise ScriptSyntaxError(
            f"{self.file_name} {token.line_number - 1}: {self.lines[token.line_number - 1]}\n {err_msg}"
        )

    def dump_vm_codes(self):
        vm_file = output.compose_compiled_file(Path(self.file_name).stem, "codes.vm")
        with open(vm_file, "w") as f:
            for vm_code in self.vm_codes:
                f.write(str(vm_code) + "\n")
