
def helper_setupA_tp(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/setupA-tp.txt

    Original DSL:
        # This is the config setup for FGT_A in TP Mode
        
        ###################################################################
        # Create vdoms
        config vdom
                edit FGT_A:VDOM1
        end
        
        
        ####################################################################
        
        config global
            config system fortiguard
                set fortiguard-anycast disable
            end
        end
        
        
        # Setup ROOT
        include testcase/GLOBAL:VERSION/ips/topology1/goroot.txt
        
        #config system settings
        #        set opmode transparent
        #        set manageip FGT_A:MANAGEIP_ROOT
        #end
        
        # Mantis: 0519574. An entry in firewall address will be automatically added for interface with role type dmz/lan. Delete these entries first before changing VDOM for them.
        # Mantis: 0523489. The address will be created again after after configuring TP mode. So need to put purge after changing opmode.
        config firewall address
        	purge
        end
        
        config firewall policy
        	purge
        end
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        
        ################################################################
        # Setup VDOM1
        include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        
        config system settings
        	set opmode transparent
        	set manageip FGT_A:MANAGEIP_VD1
        	set gui-ips enable
        	#set gui-multiple-utm-profiles enable
        end
        
        # Mantis: 0519574. An entry in firewall address will be automatically added for interface with role type dmz/lan. Delete these entries first before changing VDOM for them.
        # Mantis: 0523489. The address will be created again after after configuring TP mode. So need to put purge after changing opmode.
        config firewall address
        	purge
        end
        
        config log memory setting
            set status enable
        end
        
        config firewall policy
        	purge
        end
        config system interface
            edit FGT_A:PORT1
                set vdom FGT_A:VDOM1
                set allowaccess ping https ssh snmp http telnet
                set type physical
                config ipv6
                    set ip6-allowaccess ping https ssh snmp
                end
            next
            edit FGT_A:PORT2
                set vdom FGT_A:VDOM1
                set allowaccess ping https ssh snmp http telnet
                set type physical
                config ipv6
                    set ip6-allowaccess ping https ssh snmp
                end
            next
        end
        config firewall policy
            edit 1
                set srcintf FGT_A:PORT2
                set dstintf FGT_A:PORT1
                set srcaddr "all"
                set dstaddr "all"
                set action accept
                set schedule "always"
        		set service "ALL"
            next
            edit 2
                set srcintf FGT_A:PORT1
                set dstintf FGT_A:PORT2
                set srcaddr "all"
                set dstaddr "all"
                set action accept
                set schedule "always"                                                                                 
        		set service "ALL"                                                                           
            next                         
        end
        
        config firewall policy
            edit 11
                set srcintf FGT_A:PORT2
                set dstintf FGT_A:PORT1
                set srcaddr6 "all"
                set dstaddr6 "all"
                set action accept
                set schedule "always"
                set service "ALL"
            next
            edit 12
                set srcintf FGT_A:PORT1
                set dstintf FGT_A:PORT2
                set srcaddr6 "all"
                set dstaddr6 "all"
                set action accept
                set schedule "always"
                set service "ALL"
            next
        end
        
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        
        ################################################################
        # Go To Global
        include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt 
        
        config system global
            	set admintimeout 480
        	#set dst enable
        	set hostname "FGT-A-TP"
        	set management-vdom FGT_A:VDOM1 
        	set allow-empty-passwords enable	
        end
        
        # create a user with empty password
        config system admin
        	edit sshadmin
        		set accprofile "super_admin"
        		set vdom "root"
        # due to on v7.6.3 the new user creation needs the current password, using mynext and nan_enter instead of next. 
        	mynext
        	nan_enter
        end
        
        config system dns
            	set primary 172.17.254.148
        	unset secondary
                set protocol cleartext
        end
        
        config system console
        	set output standard
        end
        
        config system interface
        	edit PORT1
                	set vdom FGT_A:VDOM1
                	set allowaccess ping https ssh snmp http telnet
        	        set type physical
            	next
        end
        
        config system admin
            	edit FGT_A:VDOM1 
                	set accprofile "prof_admin"
                	set vdom FGT_A:VDOM1
        # due to since v7.6.3 new user creation needs the current password, using mynext and nan_enter instead of next. 
            	mynext
        		nan_enter
        end
        
        # Change port speed to 1000full for FGT3200D fiber port in local lab
        get sys status 
        #setvar -e "(?n)^Version: (.*?) v" -to PLATFORM_TYPE
        #<if $PLATFORM_TYPE eq FortiGate-3200D>
        
        setvar -e "(?n)^Serial-Number: (.*?)" -to SN
        <if $SN eq FG3K2D3Z15800141>
                config sys interface
                        edit FGT_A:PORT1
                                set speed 1000full
                        next        
                        edit FGT_A:PORT2
                                set speed 1000full
                        next
                end
        <fi>
        
        config ips global
           set database extended
        end
        
        #config log fortianalyzer setting
        #    set status enable
        #    set server FGT_A:IP_FAZ
        #end
        
        ###############################################################
        #  Exit Global
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config vdom")
    fgt.execute("edit FGT_A:VDOM1")
    fgt.execute("end")
    fgt.execute("config global")
    fgt.execute("config system fortiguard")
    fgt.execute("set fortiguard-anycast disable")
    fgt.execute("end")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/goroot.txt")
    fgt.execute("config firewall address")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config firewall policy")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt")
    fgt.execute("config system settings")
    fgt.execute("set opmode transparent")
    fgt.execute("set manageip FGT_A:MANAGEIP_VD1")
    fgt.execute("set gui-ips enable")
    fgt.execute("end")
    fgt.execute("config firewall address")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config log memory setting")
    fgt.execute("set status enable")
    fgt.execute("end")
    fgt.execute("config firewall policy")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config system interface")
    fgt.execute("edit FGT_A:PORT1")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("config ipv6")
    fgt.execute("set ip6-allowaccess ping https ssh snmp")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT2")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("config ipv6")
    fgt.execute("set ip6-allowaccess ping https ssh snmp")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config firewall policy")
    fgt.execute("edit 1")
    fgt.execute("set srcintf FGT_A:PORT2")
    fgt.execute("set dstintf FGT_A:PORT1")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set srcintf FGT_A:PORT1")
    fgt.execute("set dstintf FGT_A:PORT2")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config firewall policy")
    fgt.execute("edit 11")
    fgt.execute("set srcintf FGT_A:PORT2")
    fgt.execute("set dstintf FGT_A:PORT1")
    fgt.execute("set srcaddr6 \"all\"")
    fgt.execute("set dstaddr6 \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("next")
    fgt.execute("edit 12")
    fgt.execute("set srcintf FGT_A:PORT1")
    fgt.execute("set dstintf FGT_A:PORT2")
    fgt.execute("set srcaddr6 \"all\"")
    fgt.execute("set dstaddr6 \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt")
    fgt.execute("config system global")
    fgt.execute("set admintimeout 480")
    fgt.execute("set hostname \"FGT-A-TP\"")
    fgt.execute("set management-vdom FGT_A:VDOM1")
    fgt.execute("set allow-empty-passwords enable")
    fgt.execute("end")
    fgt.execute("config system admin")
    fgt.execute("edit sshadmin")
    fgt.execute("set accprofile \"super_admin\"")
    fgt.execute("set vdom \"root\"")
    fgt.execute("mynext")
    fgt.execute("nan_enter")
    fgt.execute("end")
    fgt.execute("config system dns")
    fgt.execute("set primary 172.17.254.148")
    fgt.execute("unset secondary")
    fgt.execute("set protocol cleartext")
    fgt.execute("end")
    fgt.execute("config system console")
    fgt.execute("set output standard")
    fgt.execute("end")
    fgt.execute("config system interface")
    fgt.execute("edit PORT1")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config system admin")
    fgt.execute("edit FGT_A:VDOM1")
    fgt.execute("set accprofile \"prof_admin\"")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("mynext")
    fgt.execute("nan_enter")
    fgt.execute("end")
    fgt.execute("get sys status")
    fgt.execute("setvar -e \"(?n)^Serial-Number: (.*?)\" -to SN")
    if fgt.testbed.env.get_dynamic_var('SN') == 'FG3K2D3Z15800141':
        fgt.execute("config sys interface")
        fgt.execute("edit FGT_A:PORT1")
        fgt.execute("set speed 1000full")
        fgt.execute("next")
        fgt.execute("edit FGT_A:PORT2")
        fgt.execute("set speed 1000full")
        fgt.execute("next")
        fgt.execute("end")
    fgt.execute("config ips global")
    fgt.execute("set database extended")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
