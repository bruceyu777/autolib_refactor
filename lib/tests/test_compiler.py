from lib.core.compiler.compiler import compiler


def test_compile():
    compiler.run("testcase/trunk/webfilter/setup_ROBOT_FGT_nat_wf.conf")
