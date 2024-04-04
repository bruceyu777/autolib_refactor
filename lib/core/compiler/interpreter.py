from pathlib import Path

from lib.services import logger, output, summary
from lib.utilities.exceptions import CompileException

from .cmd_compiler import CmdCompiler
from .vm_code import VMCode


class Interpreter:
    CODES_FILE = "codes.vm"

    def __init__(self, file_name, tokens):
        self.tokens = tokens
        self.file_name = file_name
        self.cursor = 0
        self.vm_codes = []
        self.cur_device = None
        self.devices = set()
        self.files = set()

    def is_end(self):
        return self.cursor >= len(self.tokens)

    def _add_vm_code(self, code):
        if isinstance(code, VMCode):
            self.vm_codes.append(code)
            return
        self.vm_codes.extend(code)

    def _compile_script(self):
        # breakpoint()
        token = self.cur_token()
        if token.type == "keyword":
            self._compile_statements()
        elif token.type == "symbol" and token.str == "[":
            self._compile_section()
        elif token.type == "command":
            self._compile_command()
        elif token.type == "delimiter" and token.str == "<":
            self._compile_control()
        else:
            # print(token.str)
            # breakpoint()
            raise CompileException(
                self.file_name,
                token.line_number,
                "a start of statement",
                token.str,
            )

    def _compile_control(self):
        self._parse_token(expected_str="<")
        token = self.cur_token()
        if token.str == "if":
            self._compile_if()
        elif token.str == "intset":
            self._compile_loop()
        elif token.str == "strset":
            self._compile_strset()
        elif token.str == "intchange":
            self._compile_intchange()
        else:
            self._retreat()
            self._retreat()

    def compile(self):
        while not self.is_end():
            # print(self.cur_token())
            self._compile_script()
        self.dump_vm_codes()
        return self.vm_codes, self.devices, self.files

    def dump_vm_codes(self):
        vm_file = output.compose_compiled_file(
            Path(self.file_name).stem, self.CODES_FILE
        )
        with open(vm_file, "w", encoding="utf-8") as f:
            for vm_code in self.vm_codes:
                f.write(str(vm_code) + "\n")

    def _compile_section(self):
        self._parse_token(expected_type="symbol", expected_str="[")
        token = self._parse_token(expected_type="identifier")
        self._parse_token(expected_type="symbol", expected_str="]")
        self.cur_device = token.str
        self.devices.add(self.cur_device)
        self._add_vm_code(
            VMCode(token.line_number, "switch_device", (self.cur_device,))
        )

    def _compile_forcelogin(self):
        token = self._parse_token(expected_str="forcelogin")
        self._add_vm_code(VMCode(token.line_number, "force_login", ()))
        return

    def _compile_statements(self):
        token = self.tokens[self.cursor]
        if token.str in ["comment", "Comment"]:
            self._compile_comment()
        if token.str == "expect":
            self._compile_expect()
        if token.str == "setvar":
            self._compile_setvar()
        if token.str == "varexpect":
            self._compile_varexpect()
        if token.str == "report":
            self._compile_report()
        if token.str == "sleep":
            self._compile_sleep()
        if token.str == "clearbuff":
            self._compile_clearbuff()
        if token.str == "forcelogin":
            self._compile_forcelogin()
        if token.str == "setlicense":
            self._compile_setlicense()
        if token.str == "include":
            self._compile_include()
        if token.str == "keep_running":
            self._compile_keep_running()

    def _compile_include(self):
        token = self._parse_token(expected_str="include")
        file_name = []
        line_number = token.line_number
        while not self.is_end():
            token = self._parse_token()
            if token.line_number == line_number:
                file_name.append(token.str)
            else:
                self._retreat()
                break

        file_name = "".join(str(s) for s in file_name)
        self._add_vm_code(
            VMCode(token.line_number, "call_script", (file_name,))
        )
        self.files.add(file_name)

    def _compile_command(self):
        token = self._parse_token(expected_type="command")
        vm_codes = CmdCompiler().compile(token.str, token.line_number)
        self._add_vm_code(vm_codes)

    def cur_token(self):
        return self.tokens[self.cursor] if not self.is_end() else None

    def _advance(self):
        self.cursor += 1

    def _retreat(self):
        self.cursor -= 1

    def _parse_token(self, expected_str=None, expected_type=None):
        token = self.cur_token()
        token_line_number = token.line_number
        token_str = token.str
        token_type = token.type
        if expected_str:
            if token_str != expected_str and token_str not in expected_str:
                raise CompileException(
                    self.file_name, token_line_number, expected_str, token_str
                )
        if expected_type:
            if token_type != expected_type and token_type not in expected_type:
                raise CompileException(
                    self.file_name, token_line_number, expected_type, token_type
                )
        self._advance()
        return token

    def _compile_comment(self):
        self._advance()
        token = self._parse_token(expected_type="stringConstant")
        self._add_vm_code(VMCode(token.line_number, "comment", (token.str,)))

    def _compile_setvar(self):
        self._parse_token(expected_str="setvar")
        self._parse_token(expected_str="-", expected_type="symbol")
        self._parse_token(expected_str="e", expected_type="identifier")
        token = self._parse_token(expected_type="stringConstant")
        reg_exp = token.str
        reg_exp = reg_exp.replace(r"\\d", r"\d")
        logger.info("In compile setvar, the reg_exp is %s", reg_exp)
        self._parse_token(expected_str="-", expected_type="symbol")
        self._parse_token(expected_str="to", expected_type="identifier")
        token = self._parse_token(expected_type="identifier")
        variable_name = token.str

        self._add_vm_code(
            VMCode(token.line_number, "set_var", (reg_exp, variable_name))
        )

    def _compile_report(self):
        self._parse_token(expected_str="report")
        token = self._parse_token(
            expected_type=["integerConstant", "identifier"]
        )
        self._add_vm_code(VMCode(token.line_number, "report", (token.str,)))
        summary.add_testcase(token.str)

    def _parse_expect_parameters(
        self,
        parameters,
    ):
        token = self.cur_token()
        while token and token.str == "-":
            self._parse_token(expected_str="-", expected_type="symbol")
            option = self._parse_token(
                expected_str=parameters.keys(),
                expected_type="identifier",
            )
            if option.str == "e":
                token = self._parse_token(expected_type="stringConstant")
                token_val = (
                    token.str.replace("\\\\(", "\\(")
                    .replace("\\\\)", "\\)")
                    .replace("\\\\d", "\\d")
                )
            elif option.str == "v":
                token = self._parse_token(expected_type="variable")
                token_val = token.str
            elif option.str == "for":
                token = self._parse_token(
                    expected_type=["integerConstant", "identifier"]
                )
                token_val = token.str
            elif option.str == "t":
                token = self._parse_token(expected_type="integerConstant")
                token_val = token.str
            else:
                token = self._parse_token(
                    expected_type="identifier", expected_str="match"
                )
                token_val = token.str
            parameters[option.str] = token_val
            token = self.cur_token()
        return parameters

    # expect –e <regular expression> -t <time> –for <testcase_id>
    def _compile_expect(self):
        token = self._parse_token(expected_str="expect")
        line_number = token.line_number
        parameters = {"e": None, "for": None, "t": "5", "fail": ""}
        self._parse_expect_parameters(parameters)
        self._add_vm_code(VMCode(line_number, "expect", parameters.values()))

    # varexpect -v {$variable_name} -for <testcase_id> -t <time>
    def _compile_varexpect(self):
        token = self._parse_token(expected_str="varexpect")
        line_number = token.line_number
        parameters = {"v": None, "for": None, "t": "5", "fail": ""}
        self._parse_expect_parameters(parameters)
        self._add_vm_code(
            VMCode(line_number, "var_expect", parameters.values())
        )

    # setlicense -t <license type> -for <SN|VDOM> -to <varaibal_name>
    def _compile_setlicense(self):
        self._parse_token(expected_str="setlicense")
        self._parse_token(expected_str="-", expected_type="symbol")
        self._parse_token(expected_str="t", expected_type="identifier")
        token = self._parse_token(expected_type="identifier")
        lic_type = token.str
        self._parse_token(expected_str="-", expected_type="symbol")
        self._parse_token(expected_str="for", expected_type="identifier")
        token = self._parse_token(
            expected_str=["SN", "VDOM"], expected_type="identifier"
        )
        file_name = token.str
        self._parse_token(expected_str="-", expected_type="symbol")
        self._parse_token(expected_str="to", expected_type="identifier")
        token = self._parse_token(expected_type="identifier")
        variable_name = token.str
        line_number = token.line_number
        self._add_vm_code(
            VMCode(
                line_number, "set_license", (lic_type, file_name, variable_name)
            )
        )

    def _compile_sleep(self):
        self._parse_token(expected_str="sleep")
        token = self._parse_token(expected_type="integerConstant")

        self._add_vm_code(VMCode(token.line_number, "sleep", (token.str,)))

    def _compile_clearbuff(self):
        token = self._parse_token(expected_str="clearbuff")
        self._add_vm_code(VMCode(token.line_number, "clear_buff", ()))

    def _compile_term(self):
        token = self.cur_token()
        if token.type == "variable":
            self._parse_token()
        if token.type == "identifier":
            self._parse_token()
        if token.type == "integerConstant":
            self._parse_token()
        return token

    def _compile_expression(self):
        expression_tokens = []
        token = self._compile_term()
        expression_tokens.append(token.str)

        token = self.cur_token()
        while token.type == "operator" or token.type == "symbol":
            token = self._parse_token()
            expression_tokens.append(token.str)
            token = self._compile_term()
            expression_tokens.append(token.str)
            token = self.cur_token()
        return expression_tokens

    def _look_ahead(self):
        if self.cursor + 1 >= len(self.tokens):
            return None
        return self.tokens[self.cursor + 1]

    def _is_elseif_statement(self):
        # token = self.cur_token()
        token = self.cur_token()
        next_token = self._look_ahead()
        return token.str == "<" and next_token.str == "elseif"

    def _is_if_matched_statement(self):
        token = self.cur_token()
        next_token = self._look_ahead()
        return token.str == "<" and next_token.str in ["elseif", "else", "fi"]

    def _is_elseif_matched_statement(self):
        token = self.cur_token()
        next_token = self._look_ahead()
        return token.str == "<" and next_token.str in ["elseif", "else", "fi"]

    def _is_else_matched_statement(self):
        token = self.cur_token()
        next_token = self._look_ahead()
        return token.str == "<" and next_token.str == "fi"

    def _should_not_be_eof(self):
        if self.is_end():
            self._retreat()
            token = self.cur_token()
            raise CompileException(
                self.file_name,
                token.line_number,
                "fi or elseif or else",
                "end of the file",
            )

    def _compile_if(self):
        self._parse_token(expected_str="if")
        expression_tokens = self._compile_expression()
        logger.info("The expression is: %s ", expression_tokens)
        token = self._parse_token(expected_str=">")
        # condition = " ".join(expression_tokens)
        if_vm_code = VMCode(token.line_number, "if_not_goto", expression_tokens)

        self._add_vm_code(if_vm_code)
        while not self._is_if_matched_statement():
            self._compile_script()
            self._should_not_be_eof()

        self._parse_token(expected_str="<")
        token = self._parse_token(expected_str=["elseif", "else", "fi"])
        prev_code = if_vm_code
        if token.str == "elseif":
            while token.str == "elseif":
                prev_code.add_parameter(token.line_number)
                expression_tokens = self._compile_expression()
                self._parse_token(expected_str=">")
                # condition = " ".join(expression_tokens)
                vm_code = VMCode(token.line_number, "elseif", expression_tokens)
                self._add_vm_code(vm_code)
                prev_code = vm_code

                while not self._is_elseif_matched_statement():
                    self._compile_script()
                    self._should_not_be_eof()
                self._parse_token(expected_str="<")
                token = self._parse_token(expected_str=["else", "elseif", "fi"])

        if token.str == "else":
            prev_code.add_parameter(token.line_number)
            vm_code = VMCode(token.line_number, "case_else", ())
            prev_code = vm_code
            self._add_vm_code(vm_code)
            self._parse_token(expected_str=">")
            while not self._is_else_matched_statement():
                self._compile_script()
                self._should_not_be_eof()
            self._parse_token(expected_str="<")
            token = self._parse_token(expected_str="fi")

        if token.str == "fi":
            token = self._parse_token(expected_str=">")
            prev_code.add_parameter(token.line_number)
            vm_code = VMCode(token.line_number, "endif", ())
            self._add_vm_code(vm_code)

    def _is_loop_change_statement(self):
        token = self.cur_token()
        next_token = self._look_ahead()
        return token.str == "<" and next_token.str == "intchange"
    def _is_loop_until_statement(self):
        token = self.cur_token()
        next_token = self._look_ahead()
        return token.str == "<" and next_token.str == "until"
    def _compile_loop(self):
        self._parse_token(expected_str="intset")
        var_name = self._parse_token(expected_type="identifier")
        var_value = self._parse_token(expected_type="integerConstant")
        vm_code = VMCode(
            var_name.line_number, "intset", (var_name.str, int(var_value.str))
        )
        token = self._parse_token(expected_str=">")
        self._add_vm_code(vm_code)

        self._parse_token(expected_str="<")
        loop_start = self._parse_token(expected_str="loop")
        self._parse_token(expected_str=var_name.str, expected_type="identifier")
        self._parse_token(expected_str=">")
        vm_code = VMCode(loop_start.line_number, "start_loop", ())
        self._add_vm_code(vm_code)
        while not self._is_loop_until_statement():
            self._compile_script()
            self._should_not_be_eof()

        self._parse_token(expected_str="<")
        token = self._parse_token(expected_str="until")
        expression_tokens = self._compile_expression()
        vm_code = VMCode(
            token.line_number,
            "until",
            expression_tokens + [loop_start.line_number],
        )
        self._add_vm_code(vm_code)
        self._parse_token(expected_str=">")

    def _compile_strset(self):
        self._parse_token(expected_str="strset")
        var_name = self._parse_token(expected_type="identifier")
        var_value = self._parse_token(expected_type="identifier")
        vm_code = VMCode(
            var_name.line_number, "strset", (var_name.str, var_value.str)
        )
        token = self._parse_token(expected_str=">")
        self._add_vm_code(vm_code)

    def _compile_keep_running(self):
        self._parse_token(expected_str="keep_running")
        keep_running_flag = self._parse_token(expected_type="integerConstant")
        vm_code = VMCode(keep_running_flag.line_number, "keep_running", (keep_running_flag.str,))
        self._add_vm_code(vm_code)

    def _compile_intchange(self):
        token = self._parse_token(expected_str="intchange")
        expression_tokens = self._compile_expression()
        vm_code = VMCode(token.line_number, "intchange", expression_tokens)
        self._add_vm_code(vm_code)
        self._parse_token(expected_str=">")