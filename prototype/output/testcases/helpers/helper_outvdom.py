
def helper_outvdom(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/prototype/sample_includes/outvdom.txt

    Original DSL:
        # Exit VDOM context
        # Common teardown file for IPS tests
        
        end

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("end")
