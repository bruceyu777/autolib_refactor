
def helper_govdom1(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/govdom1.txt

    Original DSL:
        config vdom
        	edit vd1

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config vdom")
    fgt.execute("edit vd1")
