
def helper_setupA_nat(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/setupA-nat.txt

    Original DSL:
        # This is the global config setup for FGT_A
        #
        
        ###############################################################
        # Create vdoms
        config vdom
            edit FGT_A:VDOM1
            next
        end
        
        ####################################################################
        # Mantis: 0519574. An entry in firewall address will be automatically added for interface with role type dmz/lan. Delete these entries first before changing VDOM for them.
        
        include testcase/GLOBAL:VERSION/ips/topology1/goroot.txt
        config firewall address
            purge
        end
        sleep 2
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        
        include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        config firewall address
            purge
        end
        sleep 2
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        
        ################################################################
        # Go To Global
        include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
        
        config system global
            set admintimeout 480
            #set dst enable
            set hostname "FGT-A"
            set timezone 04
            set management-vdom FGT_A:VDOM1
            set gui-ipv6 enable
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
        
            config ips global
                set database extended
            end
        
            config system dns
                set primary 172.17.254.148
                set secondary 10.59.254.254
                set protocol cleartext
            end
        
            config system fortiguard
                set fortiguard-anycast disable
                set update-ffdb enable
            end
        
            config system fortiguard
                set port 8888
                set protocol udp
            end
        
            #config system central-management
            #    config server-list
            #        edit 1
            #            set server-type rating
            #            set server-address 192.168.100.206
            #        next
            #    end
            #end
        
            config system console
                set output standard
            end
        
            config system interface
                edit FGT_A:PORT1
                    set mode static
                    unset ip
                next
                edit FGT_A:PORT2
                    set mode static
                    unset ip
                next
            end
            #<if FGT_A:Model eq FGT_101F>
            #        config system virtual-switch
            #            edit "lan"
            #                config port
            #                        delete "FGT_A:PORT5"
            #                end
            #            next
            #        end
            #<elseif FGT_A:Model eq FGT_61F>
            #        config system virtual-switch
            #            edit "internal"
            #                config port
            #                        delete "FGT_A:PORT5"
            #                end
            #            next
            #        end
            #<else>
            #<fi>
            config system interface
                edit FGT_A:PORT1
                    set vdom FGT_A:VDOM1
                    set ip FGT_A:IP_PORT1
                    select allowaccess ping https ssh snmp http telnet
                    set type physical
                    config ipv6
                        #                set autoconf enable
                        set ip6-address 2000:172:16:200::1/64
                        set ip6-allowaccess ping http https telnet ssh snmp
                    end
                next
                edit FGT_A:PORT2
                    set vdom FGT_A:VDOM1
                    set ip FGT_A:IP_PORT2
                    select allowaccess ping http https telnet ssh snmp
                    set type physical
                    set secondary-IP enable
                    config ipv6
                        set ip6-address 2000:10:1:100::1/64
                        set ip6-allowaccess http https ping ssh telnet
                    end
                    config secondaryip
                        edit 1
                            set ip 10.1.200.1 255.255.255.0
                            select allowaccess ping https ssh snmp http telnet fgfm
                        next
                    end
                next
                edit FGT_A:PORT5
                    set vdom FGT_A:VDOM1
                    set ips-sniffer-mode disable
                    set ip FGT_A:IP_PORT5
                    select allowaccess ping https ssh snmp http telnet
                    set type physical
                next
                edit "vlan100"
                    set vdom FGT_A:VDOM1
                    set ip 10.10.10.1 255.255.255.0
                    select allowaccess ping https ssh snmp http telnet
                    config ipv6
                        set ip6-address 2000:10:10:10::1/64
                        set ip6-allowaccess http https ping ssh telnet
                    end
                    set interface FGT_A:PORT5
                    set vlanid 100
                    set device-identification disable
                next
        
                edit FGT_A:PORT4
                    set vdom FGT_A:VDOM1
                next
        
            end
        
            # Change port speed to 1000full for FGT3200D-1 fiber port in local lab
            get sys status
            # setvar -e "(?n)^Version: (.*?) v" -to PLATFORM_TYPE
            # <if $PLATFORM_TYPE eq FortiGate-3200D>
        
            setvar -e "Serial-Number: (.*?)\n" -to SN
            <if $SN eq FG3K2D3Z15800141>
            config sys interface
                edit FGT_A:PORT1
                    set speed 1000full
                next
                edit FGT_A:PORT2
                    set speed 1000full
                next
                edit FGT_A:PORT5
                    set speed 1000full
                next
                edit FGT_A:PORT4
                    set speed 1000full
                next
                edit mgmt2
                    unset ip
                next
            end
            <fi>
        
            config ips global
                set database extended
            end
        
            # Mantis 513778 will require serial number of FAZ to be configured. If not it will require FGT to connect to FAZ to pull serial number information.
            # If FGT cannot reach FAZ, autotest will get stuck. Commenting out FAZ configuration as IPS does not use it
            #config log fortianalyzer setting
            #    set status enable
            #    set server FGT_A:IP_FAZ
            #    set upload-option realtime
            #    set reliable enable
            #end
        
            ###############################################################
            #  Exit Global
            include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config vdom")
    fgt.execute("edit FGT_A:VDOM1")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/goroot.txt")
    fgt.execute("config firewall address")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("sleep 2")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt")
    fgt.execute("config firewall address")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("sleep 2")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt")
    fgt.execute("config system global")
    fgt.execute("set admintimeout 480")
    fgt.execute("set hostname \"FGT-A\"")
    fgt.execute("set timezone 04")
    fgt.execute("set management-vdom FGT_A:VDOM1")
    fgt.execute("set gui-ipv6 enable")
    fgt.execute("end")
    fgt.execute("config system admin")
    fgt.execute("edit sshadmin")
    fgt.execute("set accprofile \"super_admin\"")
    fgt.execute("set vdom \"root\"")
    fgt.execute("mynext")
    fgt.execute("nan_enter")
    fgt.execute("end")
    fgt.execute("config ips global")
    fgt.execute("set database extended")
    fgt.execute("end")
    fgt.execute("config system dns")
    fgt.execute("set primary 172.17.254.148")
    fgt.execute("set secondary 10.59.254.254")
    fgt.execute("set protocol cleartext")
    fgt.execute("end")
    fgt.execute("config system fortiguard")
    fgt.execute("set fortiguard-anycast disable")
    fgt.execute("set update-ffdb enable")
    fgt.execute("end")
    fgt.execute("config system fortiguard")
    fgt.execute("set port 8888")
    fgt.execute("set protocol udp")
    fgt.execute("end")
    fgt.execute("config system console")
    fgt.execute("set output standard")
    fgt.execute("end")
    fgt.execute("config system interface")
    fgt.execute("edit FGT_A:PORT1")
    fgt.execute("set mode static")
    fgt.execute("unset ip")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT2")
    fgt.execute("set mode static")
    fgt.execute("unset ip")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config system interface")
    fgt.execute("edit FGT_A:PORT1")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set ip FGT_A:IP_PORT1")
    fgt.execute("select allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("config ipv6")
    fgt.execute("set ip6-address 2000:172:16:200::1/64")
    fgt.execute("set ip6-allowaccess ping http https telnet ssh snmp")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT2")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set ip FGT_A:IP_PORT2")
    fgt.execute("select allowaccess ping http https telnet ssh snmp")
    fgt.execute("set type physical")
    fgt.execute("set secondary-IP enable")
    fgt.execute("config ipv6")
    fgt.execute("set ip6-address 2000:10:1:100::1/64")
    fgt.execute("set ip6-allowaccess http https ping ssh telnet")
    fgt.execute("end")
    fgt.execute("config secondaryip")
    fgt.execute("edit 1")
    fgt.execute("set ip 10.1.200.1 255.255.255.0")
    fgt.execute("select allowaccess ping https ssh snmp http telnet fgfm")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT5")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set ips-sniffer-mode disable")
    fgt.execute("set ip FGT_A:IP_PORT5")
    fgt.execute("select allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("next")
    fgt.execute("edit \"vlan100\"")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("set ip 10.10.10.1 255.255.255.0")
    fgt.execute("select allowaccess ping https ssh snmp http telnet")
    fgt.execute("config ipv6")
    fgt.execute("set ip6-address 2000:10:10:10::1/64")
    fgt.execute("set ip6-allowaccess http https ping ssh telnet")
    fgt.execute("end")
    fgt.execute("set interface FGT_A:PORT5")
    fgt.execute("set vlanid 100")
    fgt.execute("set device-identification disable")
    fgt.execute("next")
    fgt.execute("edit FGT_A:PORT4")
    fgt.execute("set vdom FGT_A:VDOM1")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("get sys status")
    fgt.execute("setvar -e \"Serial-Number: (.*?)\\n\" -to SN")
    if fgt.testbed.env.get_dynamic_var('SN') == 'FG3K2D3Z15800141':
        fgt.execute("config sys interface")
        fgt.execute("edit FGT_A:PORT1")
        fgt.execute("set speed 1000full")
        fgt.execute("next")
        fgt.execute("edit FGT_A:PORT2")
        fgt.execute("set speed 1000full")
        fgt.execute("next")
        fgt.execute("edit FGT_A:PORT5")
        fgt.execute("set speed 1000full")
        fgt.execute("next")
        fgt.execute("edit FGT_A:PORT4")
        fgt.execute("set speed 1000full")
        fgt.execute("next")
        fgt.execute("edit mgmt2")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
    fgt.execute("config ips global")
    fgt.execute("set database extended")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
