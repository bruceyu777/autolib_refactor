
def helper_purge(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/purge.txt

    Original DSL:
        # This is a general purge file for initializing autotest after factory reset, please use 'include' to include it in [FGT_X] sections in your initializing scripts
        # Version information: 2017.04.07.1223 Model coverd (total 38): FortiGate-3240C, FortiGateRugged-60D, FortiGate-50E, FortiGate-51E, FortiGate-52E, FortiGate-60E, FortiGate-80C, FortiGate-80D, FortiGate-81E, FortiGate-81E-POE, FortiGate-90D, FortiGate-90D-POE, FortiGate-90E, FortiGate-91E, FortiGate-94D-POE, FortiGate-100D, FortiGate-100E, FortiGate-101E, FortiGate-140D, FortiGate-140D-POE, FortiGate-140D-POE-T1, FortiGate-200D, FortiGate-280D-POE, FortiGate-300D, FortiGate-400D, FortiGate-500D, FortiGate-600D, FortiGate-800D, FortiGate-900D, FortiGate-1000D, FortiGate-1500D, FortiGate-3200D, FortiCarrier-3700DX, FortiGate-3800D, FortiGate-2500E, FortiWiFi-60D, FortiWiFi-61E, FortiWiFi-92D
        # CLI is wrotten based on v5.4 by RAIN, any question or issue, please contact: rainxiao@fortinet.com, phone: 6421
        
        comment Start to purge settings on FGT by purge.txt
        
        config system console
            set output standard
        end
        
        config system dhcp server
            purge
        end
        
        #skip router static purge for FGT_VM to keep network settings for VM license check
        <if FGT_A:VM eq yes>
        <else>
        config router static
            purge
        end
        <fi>
        
        config firewall policy
            purge
        end
        
        config firewall vip
            purge
        end
        
        config firewall sniffer
            purge
        end
        
        config firewall address
            purge
        end
        
        config vpn ipsec concentrator
            purge
        end 
        
        config vpn ipsec phase2-interface
            purge
        end
        
        config vpn ipsec phase1-interface
            purge
        end
        
        config vpn ipsec phase2
            purge
        end
        
        config vpn ipsec phase1
            purge
        end
        
        config vpn ipsec manualkey-interface
            purge
        end
        
        config vpn ipsec manualkey
            purge
        end
        
        config user group
            purge
        end
        
        config user local
            purge
        end
        
        config user radius
            purge
        end
        
        config user ldap
            purge
        end
        
        config user tacacs+
            purge
        end
        
        config system ha
            unset mode
        end
        
        config system virtual-wire-pair
        	purge
        end
        
        config system virtual-switch
                purge
        end
        
        #skip dns unset for FGT_VM to keep network settings for VM license check
        <if FGT_A:VM eq yes>
        <else>
        config system dns
            unset primary
            unset secondary
        end
        <fi>
        
        config system auto-install
            set auto-install-config disable
            set auto-install-image disable
        end
        
            config system interface
                edit fortilink
                    unset member
                next
            end
        
        get sys status 
        setvar -e "(?n)^Version: (.*?) v" -to HARDWARE_TYPE
        
        <if $HARDWARE_TYPE eq FortiGate-61F>  
            config system interface
                edit fortilink
                    unset member
                next
            end
            config system global
                set proxy-and-explicit-proxy enable
            end
        <elseif $HARDWARE_TYPE eq FortiGate-101F> 
            config system interface
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit fortilink
                    unset member
                next
            end
        #    config sys virtual-switch
        #	edit lan
        #	    config port
        #		del port1
        #	    end
        #    end
        <elseif $HARDWARE_TYPE eq FortiGate-3240C>
            config system interface
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit fortilink
                    unset member
                next
            end
        
        <elseif $HARDWARE_TYPE eq FortiGateRugged-60D>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
            end
            config system virtual-switch
                purge
            end
        <elseif $HARDWARE_TYPE eq FortiGate-50E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-51E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-52E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-60E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next        
            end   
        
            config system virtual-switch
                purge
                edit "internal"
                   config port
                        delete "internal1"
                   end
                end
            end
            config system global
                set proxy-and-explicit-proxy enable
            end
        <elseif $HARDWARE_TYPE eq FortiGate-80C>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-80D>
            config system interface
                edit "port1"
                    set mode static
                    unset ip
                next        
            end   
        
        <elseif $HARDWARE_TYPE eq FortiGate-81E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
                edit "ha"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-81E-POE>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
                edit "ha"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-90D>
            
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
            end  
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-90D-POE>
            
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "internalA"
                    set mode static
                    unset ip 
                next
                edit "internalB"
                    set mode static
                    unset ip 
                next
                edit "internalC"
                    set mode static
                    unset ip 
                next
                edit "internalD"
                    set mode static
                    unset ip 
                next
            end  
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-90E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
                edit "ha"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-91E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip 
                next
                edit "wan2"
                    set mode static
                    unset ip 
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
                edit "ha"
                    set mode static
                    unset ip 
                next
            end   
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-94D-POE>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip            
                next
                edit "wan2"
                    set mode static
                    unset ip            
                next
                edit "dmz1"
                    unset ip
                next
                edit "dmz2"
                    unset ip
                next
            end
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-100D>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
            end
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-100E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
                edit "ha1"
                    set mode static
                    unset ip 
                next
                edit "ha2"
                    set mode static
                    unset ip 
                next                
            end
        
            config system virtual-switch
                purge
            end 
        
        <elseif $HARDWARE_TYPE eq FortiGate-101E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz"
                    set mode static
                    unset ip 
                next
                edit "ha1"
                    set mode static
                    unset ip 
                next
                edit "ha2"
                    set mode static
                    unset ip 
                next                
            end
        
            config system virtual-switch
                purge
            end 
        
        <elseif $HARDWARE_TYPE eq FortiGate-140D>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz1"
                    unset ip 
                next
            end
        
            config system virtual-switch
                purge
            end 
        
        <elseif $HARDWARE_TYPE eq FortiGate-140D-POE>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz1"
                    unset ip 
                next
            end
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-140D-POE-T1>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz1"
                    unset ip 
                next
                edit "dmz2"
                    unset ip 
                next
            end
        
            config system virtual-switch
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-200D>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "dmz1"
                    unset ip 
                next
            end
        
            config system virtual-switch
                purge
            end 
        
        <elseif $HARDWARE_TYPE eq FortiGate-280D-POE>
            config system interface
                edit "dmz1"
                    unset ip
                next
                edit "mgmt"
                    unset ip
                    unset dedicated-to
                next
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next        
            end   
            config system virtual-switch
                delete lan1
            end 
        
        <elseif $HARDWARE_TYPE eq FortiGate-300D>
            config system interface
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
                edit "port1"
                    unset ip
                next
                edit "port4"
                    set ips-sniffer-mode disable
                next
                edit "port8"
                    set ips-sniffer-mode disable
                next
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-400D>
            config system interface
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
                edit "port1"
                    unset ip
                next
                edit "port5"
                    set ips-sniffer-mode disable
                next
                edit "port6"
                    set ips-sniffer-mode disable
                next
                edit "port13"
                    set ips-sniffer-mode disable
                next
                edit "port14"
                    set ips-sniffer-mode disable
                next        
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-500D>
            config system interface
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
                edit "port1"
                    unset ip
                next
                edit "port5"
                    set ips-sniffer-mode disable
                next
                edit "port6"
                    set ips-sniffer-mode disable
                next
                edit "port13"
                    set ips-sniffer-mode disable
                next
                edit "port14"
                    set ips-sniffer-mode disable
                next
            end
        
            config system virtual-wire-pair
                purge
            end 
        
        <elseif $HARDWARE_TYPE eq FortiGate-600D>
            config system interface
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
                edit "port1"
                    unset ip
                next
                edit "port5"
                    set ips-sniffer-mode disable
                next
                edit "port6"
                    set ips-sniffer-mode disable
                next
                edit "port13"
                    set ips-sniffer-mode disable
                next
                edit "port14"
                    set ips-sniffer-mode disable
                next        
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-800D>
            config system interface
                edit "port1"
                    unset ip
                next
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next        
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-900D>
            config system interface
                edit "port1"
                    unset ip
                next
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end    
        
        <elseif $HARDWARE_TYPE eq FortiGate-1000D>
            config system interface
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-1500D>
            config system interface
                edit "port1"
                    unset ip
                next
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end    
        
        <elseif $HARDWARE_TYPE eq FortiGate-3200D>
            config system interface
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end 
        
        <elseif $HARDWARE_TYPE eq FortiCarrier-3700DX>
            config system interface
                edit "port1"
                    unset ip
                next
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-3800D>
            config system interface
                edit "port1"
                    unset ip
                next
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end
        
        <elseif $HARDWARE_TYPE eq FortiGate-2500E>
            config system interface
                edit "port1"
                    unset ip
                next
                edit "mgmt1"
                    unset ip
                    unset dedicated-to
                next
                edit "mgmt2"
                    unset ip
                    unset dedicated-to
                next
            end
        
        <elseif $HARDWARE_TYPE eq FortiWiFi-60D>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "dmz"
                    unset ip
                next
            end
            config system switch-interface
                purge
            end
        
            sleep 5
        
            config system virtual-switch
                purge
            end
        
            sleep 5
            
            config wireless-controller wtp
                edit FWF60D-WIFI0
                    unset wtp-profile
                next
            end
        
            config wireless-controller vap
                purge
            end
        
        
        <elseif $HARDWARE_TYPE eq FortiWiFi-61E>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "dmz"
                    unset ip
                next
            end
            config system switch-interface
                purge
            end
        
            sleep 5
        
            config system virtual-switch
                purge
            end
        
            sleep 5
            
            config wireless-controller wtp
                edit FWF61E-WIFI0
                    unset wtp-profile
                next
            end
        
            config wireless-controller vap-group
                purge
            end
        
            config wireless-controller vap
                purge
            end
        
        <elseif $HARDWARE_TYPE eq FortiWiFi-92D>
            config system interface
                edit "wan1"
                    set mode static
                    unset ip
                next
                edit "wan2"
                    set mode static
                    unset ip
                next
                edit "dmz"
                    unset ip
                next
            end
            config system switch-interface
                purge
            end
        
            sleep 5
        
            config system virtual-switch
                purge
            end
        
            sleep 5
            
            config wireless-controller wtp
                edit "FWF92D-WIFI0"
                    unset wtp-profile
                next
            end
        
            config wireless-controller vap
                purge
            end    
            
        <else>
        
        <fi>
        
        sleep 5

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("comment Start to purge settings on FGT by purge.txt")
    fgt.execute("config system console")
    fgt.execute("set output standard")
    fgt.execute("end")
    fgt.execute("config system dhcp server")
    fgt.execute("purge")
    fgt.execute("end")
    if fgt.testbed.read_env_variables('FGT_A:VM') == 'yes':
        pass
    else:
        fgt.execute("config router static")
        fgt.execute("purge")
        fgt.execute("end")
    fgt.execute("config firewall policy")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config firewall vip")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config firewall sniffer")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config firewall address")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec concentrator")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec phase2-interface")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec phase1-interface")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec phase2")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec phase1")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec manualkey-interface")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config vpn ipsec manualkey")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config user group")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config user local")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config user radius")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config user ldap")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config user tacacs+")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config system ha")
    fgt.execute("unset mode")
    fgt.execute("end")
    fgt.execute("config system virtual-wire-pair")
    fgt.execute("purge")
    fgt.execute("end")
    fgt.execute("config system virtual-switch")
    fgt.execute("purge")
    fgt.execute("end")
    if fgt.testbed.read_env_variables('FGT_A:VM') == 'yes':
        pass
    else:
        fgt.execute("config system dns")
        fgt.execute("unset primary")
        fgt.execute("unset secondary")
        fgt.execute("end")
    fgt.execute("config system auto-install")
    fgt.execute("set auto-install-config disable")
    fgt.execute("set auto-install-image disable")
    fgt.execute("end")
    fgt.execute("config system interface")
    fgt.execute("edit fortilink")
    fgt.execute("unset member")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("get sys status")
    fgt.execute("setvar -e \"(?n)^Version: (.*?) v\" -to HARDWARE_TYPE")
    if fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-61F':
        fgt.execute("config system interface")
        fgt.execute("edit fortilink")
        fgt.execute("unset member")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system global")
        fgt.execute("set proxy-and-explicit-proxy enable")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-101F':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit fortilink")
        fgt.execute("unset member")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-3240C':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit fortilink")
        fgt.execute("unset member")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGateRugged-60D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-50E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-51E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-52E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-60E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("edit \"internal\"")
        fgt.execute("config port")
        fgt.execute("delete \"internal1\"")
        fgt.execute("end")
        fgt.execute("end")
        fgt.execute("end")
        fgt.execute("config system global")
        fgt.execute("set proxy-and-explicit-proxy enable")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-80C':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-80D':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-81E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-81E-POE':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-90D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-90D-POE':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"internalA\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"internalB\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"internalC\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"internalD\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-90E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-91E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-94D-POE':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz2\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-100D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-100E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-101E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"ha2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-140D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-140D-POE':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-140D-POE-T1':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz2\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-200D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"dmz1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-280D-POE':
        fgt.execute("config system interface")
        fgt.execute("edit \"dmz1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-switch")
        fgt.execute("delete lan1")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-300D':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"port4\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port8\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-400D':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"port5\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port6\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port13\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port14\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-500D':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"port5\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port6\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port13\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port14\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system virtual-wire-pair")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-600D':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"port5\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port6\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port13\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("edit \"port14\"")
        fgt.execute("set ips-sniffer-mode disable")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-800D':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-900D':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-1000D':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-1500D':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-3200D':
        fgt.execute("config system interface")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiCarrier-3700DX':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-3800D':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiGate-2500E':
        fgt.execute("config system interface")
        fgt.execute("edit \"port1\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"mgmt1\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("edit \"mgmt2\"")
        fgt.execute("unset ip")
        fgt.execute("unset dedicated-to")
        fgt.execute("next")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiWiFi-60D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system switch-interface")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("sleep 5")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("sleep 5")
        fgt.execute("config wireless-controller wtp")
        fgt.execute("edit FWF60D-WIFI0")
        fgt.execute("unset wtp-profile")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config wireless-controller vap")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiWiFi-61E':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system switch-interface")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("sleep 5")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("sleep 5")
        fgt.execute("config wireless-controller wtp")
        fgt.execute("edit FWF61E-WIFI0")
        fgt.execute("unset wtp-profile")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config wireless-controller vap-group")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("config wireless-controller vap")
        fgt.execute("purge")
        fgt.execute("end")
    elif fgt.testbed.env.get_dynamic_var('HARDWARE_TYPE') == 'FortiWiFi-92D':
        fgt.execute("config system interface")
        fgt.execute("edit \"wan1\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"wan2\"")
        fgt.execute("set mode static")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("edit \"dmz\"")
        fgt.execute("unset ip")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config system switch-interface")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("sleep 5")
        fgt.execute("config system virtual-switch")
        fgt.execute("purge")
        fgt.execute("end")
        fgt.execute("sleep 5")
        fgt.execute("config wireless-controller wtp")
        fgt.execute("edit \"FWF92D-WIFI0\"")
        fgt.execute("unset wtp-profile")
        fgt.execute("next")
        fgt.execute("end")
        fgt.execute("config wireless-controller vap")
        fgt.execute("purge")
        fgt.execute("end")
    fgt.execute("sleep 5")
