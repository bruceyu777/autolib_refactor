
def helper_downPort(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/downPort.txt

    Original DSL:
        config system interface
        	edit FGT_A:PORT6
        		set status down
        	next
        	edit FGT_A:PORT7
        		set status down
        	next
        	edit FGT_A:PORT8
        		set status down
        	next
        	edit FGT_A:PORT9
        		set status down
        	next	
        end

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config system interface")
    fgt.execute("edit FGT_A:PORT6")
    fgt.execute("set status down")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT7")
    fgt.execute("set status down")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT8")
    fgt.execute("set status down")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT9")
    fgt.execute("set status down")
    fgt.execute("next")
    fgt.execute("end")
