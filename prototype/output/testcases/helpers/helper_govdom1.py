
def helper_govdom1(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/prototype/sample_includes/govdom1.txt

    Original DSL:
        # Enter government VDOM (vd1)
        # This is a common setup file used by many IPS tests
        
        config vdom
            edit vd1

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config vdom")
    fgt.execute("edit vd1")
