
def helper_setupC(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/setupC.txt

    Original DSL:
        # This is the config setup for FGT_C
        
        config system global
            set admintimeout 480
            #set dst enable
            set hostname "FGT-C"
        end
        
        config system admin
            edit sshadmin
                set accprofile "super_admin"
                set vdom "root"
                # due to on v7.6.3 the new user creation needs the current password, using mynext and nan_enter instead of next.
                mynext
                nan_enter
            end
        
            config system fortiguard
                set fortiguard-anycast disable
                set update-ffdb enable
            end
        
            # config system interface
            config system interface
                edit PORT1
                    set vdom "root"
                    set mode static
                    set ip FGT_C:IP_PORT1
                    select allowaccess ping https ssh snmp http telnet
                    set type physical
                next
                edit PORT2
                    set vdom "root"
                    set mode static
                    set ip FGT_C:IP_PORT2
                    select allowaccess ping https ssh snmp http telnet
                    set type physical
                next
            end
        
            # add firewall policy for the vlan interfacesa
            config firewall address
                edit all
                next
            end
        
            config firewall policy
                edit 1
                    set srcintf FGT_C:PORT2
                    set dstintf FGT_C:PORT1
                    set srcaddr "all"
                    set dstaddr "all"
                    set action accept
                    set schedule "always"
                    set service "ALL"
                    set nat enable
                next
                edit 2
                    set srcintf FGT_C:PORT1
                    set dstintf FGT_C:PORT2
                    set srcaddr "all"
                    set dstaddr "all"
                    set action accept
                    set schedule "always"
                    set service "ALL"
                    set nat enable
                next
            end
        
            config router static
                edit 1
                    set device FGT_C:PORT1
                    set gateway FGT_C:GATEWAY
                next
                edit 2
                    set device FGT_C:PORT1
                    set dst 10.1.100.0 255.255.255.0
                    set gateway 172.16.200.1
                next
                edit 2
                    set device FGT_C:PORT1
                    set dst 10.1.100.0 255.255.255.0
                    set gateway 172.16.200.1
                next
                edit 3
                    set device FGT_C:PORT1
                    set dst 10.10.10.0 255.255.255.0
                    set gateway 172.16.200.1
                next
        
            end
        
            config log memory setting
                set status enable
            end
        
            #config log memory filter
            #    set event enable
            #    set admin enable
            #    set auth enable
            #    set dhcp enable
            #    set ha enable
            #    set ipsec enable
            #    set ldb-monitor enable
            #    set pattern enable
            #    set ppp enable
            #    set sslvpn-log-adm enable
            #    set sslvpn-log-auth enable
            #    set sslvpn-log-session enable
            #    set system enable
            #end
        
            config system snmp community
                edit 1
                    set events cpu-high mem-low log-full intf-ip vpn-tun-up vpn-tun-down ha-switch ha-hb-failure ips-signature ips-anomaly av-virus av-oversize av-pattern av-fragmented fm-if-change ha-member-up ha-member-down ent-conf-change faz-disconnect
                    config hosts
                        edit 1
                            #set interface "port2"
                            set ip 10.1.100.11 255.255.255.255
                        next
                    end
                    set name "public"
                    set query-v1-port 10161
                    set query-v2c-port 10161
                    set trap-v1-lport 10162
                    set trap-v1-rport 10162
                    set trap-v2c-lport 10162
                    set trap-v2c-rport 10162
                next
            end
        
            config system snmp sysinfo
                set contact-info "Frank"
                set description "fgtC"
                set location "Burnaby"
                set status enable
            end
        
            config system dns
                set primary 172.17.254.148
                set secondary 10.59.254.254
                set protocol cleartext
            end
        
            diag sys session clear

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("config system global")
    fgt.execute("set admintimeout 480")
    fgt.execute("set hostname \"FGT-C\"")
    fgt.execute("end")
    fgt.execute("config system admin")
    fgt.execute("edit sshadmin")
    fgt.execute("set accprofile \"super_admin\"")
    fgt.execute("set vdom \"root\"")
    fgt.execute("mynext")
    fgt.execute("nan_enter")
    fgt.execute("end")
    fgt.execute("config system fortiguard")
    fgt.execute("set fortiguard-anycast disable")
    fgt.execute("set update-ffdb enable")
    fgt.execute("end")
    fgt.execute("config system interface")
    fgt.execute("edit PORT1")
    fgt.execute("set vdom \"root\"")
    fgt.execute("set mode static")
    fgt.execute("set ip FGT_C:IP_PORT1")
    fgt.execute("select allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("next")
    fgt.execute("edit PORT2")
    fgt.execute("set vdom \"root\"")
    fgt.execute("set mode static")
    fgt.execute("set ip FGT_C:IP_PORT2")
    fgt.execute("select allowaccess ping https ssh snmp http telnet")
    fgt.execute("set type physical")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config firewall address")
    fgt.execute("edit all")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config firewall policy")
    fgt.execute("edit 1")
    fgt.execute("set srcintf FGT_C:PORT2")
    fgt.execute("set dstintf FGT_C:PORT1")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("set nat enable")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set srcintf FGT_C:PORT1")
    fgt.execute("set dstintf FGT_C:PORT2")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("set nat enable")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config router static")
    fgt.execute("edit 1")
    fgt.execute("set device FGT_C:PORT1")
    fgt.execute("set gateway FGT_C:GATEWAY")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set device FGT_C:PORT1")
    fgt.execute("set dst 10.1.100.0 255.255.255.0")
    fgt.execute("set gateway 172.16.200.1")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set device FGT_C:PORT1")
    fgt.execute("set dst 10.1.100.0 255.255.255.0")
    fgt.execute("set gateway 172.16.200.1")
    fgt.execute("next")
    fgt.execute("edit 3")
    fgt.execute("set device FGT_C:PORT1")
    fgt.execute("set dst 10.10.10.0 255.255.255.0")
    fgt.execute("set gateway 172.16.200.1")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config log memory setting")
    fgt.execute("set status enable")
    fgt.execute("end")
    fgt.execute("config system snmp community")
    fgt.execute("edit 1")
    fgt.execute("set events cpu-high mem-low log-full intf-ip vpn-tun-up vpn-tun-down ha-switch ha-hb-failure ips-signature ips-anomaly av-virus av-oversize av-pattern av-fragmented fm-if-change ha-member-up ha-member-down ent-conf-change faz-disconnect")
    fgt.execute("config hosts")
    fgt.execute("edit 1")
    fgt.execute("set ip 10.1.100.11 255.255.255.255")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("set name \"public\"")
    fgt.execute("set query-v1-port 10161")
    fgt.execute("set query-v2c-port 10161")
    fgt.execute("set trap-v1-lport 10162")
    fgt.execute("set trap-v1-rport 10162")
    fgt.execute("set trap-v2c-lport 10162")
    fgt.execute("set trap-v2c-rport 10162")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config system snmp sysinfo")
    fgt.execute("set contact-info \"Frank\"")
    fgt.execute("set description \"fgtC\"")
    fgt.execute("set location \"Burnaby\"")
    fgt.execute("set status enable")
    fgt.execute("end")
    fgt.execute("config system dns")
    fgt.execute("set primary 172.17.254.148")
    fgt.execute("set secondary 10.59.254.254")
    fgt.execute("set protocol cleartext")
    fgt.execute("end")
    fgt.execute("diag sys session clear")
