from lib.core.compiler.lexer import FileParser
from lib.core.compiler.syntax import SyntaxAnalyzer


class TestAnalyzer:
    def test_basic(self):
        str = """#comment: this is a test.
#include /home/zhaodonglin/test.txt
sleep 30 # this is a test
<strset CHKSUM ->
<strset DFS_CHAN 52 56 60 64 100 104 108 112 116 120 124 128 132 136 140>
<listset LAN_LIST 11C 14C 21D 24D 25D>
[FGT_A]
<while>
get system status
expect -e "(.*?)contain a data leak(.*?)" -for 591917 -t 15
<endwhile $x<1>
[FGT_A]
<intset x 3>
<if $x > 3>
    config global
<elseif $x > 4>
    config vdom
    edit root
<else>
    config system admin
<fi >
[FGT_A]
<loop>
    config system admin
    setvar -e "heel" -to x
    setvar -e "(global:.*)(\[\r\n].*)" -to "string1"
<until $i>3>
<html>


"""

        file_name = "test.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(str)
        tokens, lines = FileParser(file_name).parse()
        vm_codes = SyntaxAnalyzer(file_name, tokens, lines).analyze()
        for vm_code in vm_codes:
            print(vm_code)
        # breakpoint()
        print(vm_codes)
