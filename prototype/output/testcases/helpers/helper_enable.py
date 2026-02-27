
def helper_enable(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/enable.txt

    Original DSL:
        config sys global
               set vdom-mode multi-vdom
        end

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config sys global")
    fgt.execute("set vdom-mode multi-vdom")
    fgt.execute("end")
