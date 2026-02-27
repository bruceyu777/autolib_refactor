
def helper_goroot(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/goroot.txt

    Original DSL:
        config vdom
        	edit root

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config vdom")
    fgt.execute("edit root")
