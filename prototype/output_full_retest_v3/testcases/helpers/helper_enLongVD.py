
def helper_enLongVD(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/enLongVD.txt

    Original DSL:
        include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
        
        config system global
        	set long-vdom-name enable
        end
        
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt

    Parameters:
        fgt: FluentFortiGate device instance
    """
    from .helper_goglobal import helper_goglobal
    from .helper_outvdom import helper_outvdom
    helper_goglobal(fgt)
    fgt.execute("config system global")
    fgt.execute("set long-vdom-name enable")
    fgt.execute("end")
    helper_outvdom(fgt)
