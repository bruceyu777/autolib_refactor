
def helper_initializeA_nat(fgt):
    """
    Auto-generated from: /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/initializeA-nat.txt

    Original DSL:
        # basic config for each vdom on FGT_A
        
        ######################################################
        # Go To vd1
        include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        
        # For VM, static route is not purged in purge.txt for VM license check. So purge the entries here and add entry for PORT1 immediately to avoid long-time network connection loss.
        <if FGT_A:VM eq yes>
        config router static
            purge
        end
        <fi>
        
        config router static
            edit 1
                set device FGT_A:PORT1
                set gateway 172.16.200.254
            next
        end
        
        get sys status
        setvar -e "(?n)^Version: (.*?) v" -to PLATFORM_TYPE
        
        # FGT200E has no disk
        #<if $PLATFORM_TYPE eq FortiGate-200E>
        <if FGT_A:LOG_DEVICE eq memory>
        config log memory filter
            set severity information
        end
        <else>
        config log disk setting
            set status enable
        end
        <fi>
        
        config log memory setting
            set status enable
        end
        
        config log setting
            set local-out disable
        end
        
        config firewall address
            edit all
            next
        end
        
        config firewall ssl-ssh-profile
            edit "new-deep-inspection"
                config https
                    set ports 443
                end
                config ftps
                    set ports 990
                end
                config imaps
                    set ports 993
                end
                config pop3s
                    set ports 995
                end
                config smtps
                    set ports 465
                end
                config ssl-exempt
                    purge
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
                set nat disable
                set utm-status enable
                set profile-type single
                set profile-protocol-options "default"
                set ssl-ssh-profile "new-deep-inspection"
            next
            edit 2
                set srcintf FGT_A:PORT1
                set dstintf FGT_A:PORT2
                set srcaddr "all"
                set dstaddr "all"
                set action accept
                set schedule "always"
                set service "ALL"
                set nat disable
                set utm-status enable
                #set utm-status enable
                set profile-type single
                set profile-protocol-options "default"
                set ssl-ssh-profile "new-deep-inspection"
            next
            edit 3
                set srcintf vlan100
                set dstintf FGT_A:PORT1
                set srcaddr "all"
                set dstaddr "all"
                set action accept
                set schedule "always"
                set service "ALL"
                set nat disable
                set utm-status enable
                set profile-type single
                set profile-protocol-options "default"
                set ssl-ssh-profile "new-deep-inspection"
            next
            edit 4
                set srcintf FGT_A:PORT1
                set dstintf "vlan100"
                set srcaddr "all"
                set dstaddr "all"
                set action accept
                set schedule "always"
                set service "ALL"
                set nat disable
                set utm-status enable
                set profile-type single
                set profile-protocol-options "default"
                set ssl-ssh-profile "new-deep-inspection"
            next
        end
        
        config firewall address6
            edit "all"
            next
            edit "add6-1"
                set ip6 2000:10:1:100::22/128
            next
            edit "add6-2"
                set ip6 2000:172:16:200::/64
            next
        end
        #0574376 remove firewall policy6 to firewall policy 11-12
        config firewall policy
            edit 11
                set srcintf FGT_A:PORT2
                set dstintf FGT_A:PORT1
                set srcaddr6 "all"
                set dstaddr6 "all"
                set action accept
                set schedule "always"
                set service "ALL"
                set utm-status enable
                set profile-type single
                set profile-protocol-options "default"
                set ssl-ssh-profile "new-deep-inspection"
            next
            edit 12
                set srcintf FGT_A:PORT1
                set dstintf FGT_A:PORT2
                set srcaddr6 "all"
                set dstaddr6 "all"
                set action accept
                set schedule "always"
                set service "ALL"
                set utm-status enable
                set profile-type single
                set profile-protocol-options "default"
                set ssl-ssh-profile "new-deep-inspection"
            next
        end
        
        config dlp filepattern
            edit 3
                set name "flow-dlp"
                config entries
                    edit "Executable (exe)"
                        set filter-type type
                        set file-type exe
                    next
                end
            next
        end
        
        config dlp profile
            edit "flow-dlp"
                config rule
                    edit 1
                        set proto http-get http-post
                        set filter-by none
                        set file-type 3
                        set action block
                    next
                end
            next
        end
        
        config application custom
            edit "custom-app"
                set comment "this is one test app signature"
                set signature "F-SBID( --name \"test_custom\"; --vuln_id 9998; --attack_id 9652; --protocol tcp; --default_action pass; --tag set,Tag.xvpn.ProH.TCP.Set; --revision 3029; --app_cat 12; --technology 1; --pop High; --risk Medium; --severity info; --app Other; --os All; --status disable; --service HTTP; --flow from_server; --file_type PDF; )"
            next
        end
        
        config application list
            edit "app-list-11"
                #set log enable
        
                config entries
                    edit 1
                        set application 15832 31077 15886 15817 9998
                    next
                    edit 2
                        set action reset
                        set application 18094 15879
        
                    next
                    edit 3
                        set action pass
                        set application 15896 16337
        
                        set shaper "guarantee-100kbps"
                        set shaper-reverse "guarantee-100kbps"
                    next
                    edit 4
                        set action pass
                        set application 24818
                    next
                    edit 5
                        set category 2
                    next
                end
            next
        end
        
        config ips custom
            edit "Heartbeat.Signature"
                set comment ''
                set signature "F-SBID( --attack_id 9999; --name Heartbeat.Signature; --revision 1; --protocol tcp; --tcp_flags S; --flow from_client; --src_addr [216.54.170.245, 10.1.100.11]; --dst_port 22; --default_action pass;)"
            next
            edit "test"
                set comment ''
                set signature "F-SBID( --name \"test\"; --attack_id 6406; --tag set,Tag.xvpn.ProH.TCP.Set; --severity low; --protocol tcp; --pattern \"ABCDEFG\";)"
            next
            edit "match small"
                set comment ''
                set signature "F-SBID( --attack_id 5835;  --name \"match small\"; --default_action pass; --service http; --protocol tcp; --pattern \"small\"; --severity info; )"
            next
            edit "match Passive FTP"
                set comment ''
                set signature "F-SBID( --attack_id 5277;  --name \"match Passive FTP\";  --protocol tcp;  --src_port 21; --pattern \"Passive\"; --severity medium; --status disable;)"
            next
        end
        
        config ips sensor
            edit "sensor-11"
                config entries
                    edit 1
                        set action block
                        set log-packet enable
                        set rule 29844
                        set status enable
                    next
                    edit 2
                        set action reset
                        set log-packet enable
                        set rule 5835
                        set status enable
                    next
                    edit 3
                        set action block
                        set log-packet enable
                        set quarantine attacker
                        set rule 12705
                        set status enable
                    next
                    edit 4
                        set action pass
                        set log-packet enable
                        set rule 109445125
                        set status enable
                    next
                    edit 5
                        set application Sun
                        set location client
                        set os Windows
                        set protocol HTTP
                        set severity high critical
                    next
                end
            next
        end
        
        config application list
            edit "im_app"
                config entries
                    edit 1
                        set application 16784 11203 16640 11580 16073 16783 108855300 14576 16538
                        set session-ttl 200
                    next
                end
            next
        end
        
        config antivirus profile
            edit "AV-flow"
                set comment "flow-based scan and delete virus"
                config http
                    set av-scan block
                end
                config ftp
                    set av-scan block
                end
                config imap
                    set av-scan block
                end
                config pop3
                    set av-scan block
                end
                config smtp
                    set av-scan block
                end
            next
        end
        
        config webfilter urlfilter
            edit 1
                set name "web-filter-flow"
                config entries
                    edit 1
                        set url "www.apple.com"
                        set action block
                    next
                    edit 2
                        set url "ControlPC.qa.fortinet.com"
                        set action monitor
                    next
                end
            next
        end
        
        config webfilter profile
            edit "web-filter-flow"
                set comment "Flow-based web filter profile."
                config override
                    set ovrd-user-group ""
                end
                config web
                    set urlfilter-table 1
                end
                config ftgd-wf
                    unset options
                    config filters
                        edit 6
                            set category 12
                        next
                        edit 2
                            set category 7
                            set action block
                        next
                        edit 4
                            set category 9
                            set action block
                        next
                        edit 14
                            set category 64
                            set action block
                        next
                        edit 1
                            set category 2
                            set action block
                        next
                        edit 9
                            set category 15
                            set action block
                        next
                        edit 5
                            set category 11
                            set action block
                        next
                        edit 16
                            set category 66
                            set action block
                        next
                        edit 12
                            set category 57
                            set action block
                        next
                        edit 7
                            set category 13
                            set action block
                        next
                        edit 3
                            set category 8
                            set action block
                        next
                        edit 8
                            set category 14
                            set action block
                        next
                        edit 13
                            set category 63
                            set action block
                        next
                        edit 17
                            set category 67
                            set action block
                        next
                        edit 15
                            set category 65
                            set action block
                        next
                        edit 10
                            set category 16
                            set action block
                        next
                        edit 18
                            set category 26
                            set action block
                        next
                        edit 11
                        next
                    end
                end
            next
        end
        
        config emailfilter block-allow-list
            edit 1
                config entries
                    edit 1
                        set ip4-subnet 172.16.200.0 255.255.255.0
                    next
                    edit 2
                        set type email-from
                        set pattern "tester@ControlPC.qa.fortinet.com"
                    next
                end
                set name "flow-spam"
            next
        end
        
        config emailfilter profile
            edit "flow-spam"
                set spam-filtering enable
                #        set options spambal spamfsip spamfssubmit spamfschksum spamfsurl spamfsphish
                set options spambal
                set spam-bal-table 1
            next
        end
        #disable proxy-inline-ips to test engine behavior, enable this option for new cases individually#
        config ips settings
            set proxy-inline-ips disable
        end
        
        diag sys session clear
        sleep 5
        diag de crashlog clear
        sleep 5
        
        ##################################################
        #  This is for exiting the vd1
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        
        #####################################################
        # Go To Root Vdom
        include testcase/GLOBAL:VERSION/ips/topology1/goroot.txt
        
        config firewall address
            edit all
            next
        end
        
        #####################################################
        #  This is for exiting the Root
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        
        #####################################################
        include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        # This is to update IPS definition and engine
        #due to bug 0704389, ips profile need to be enabled in policies to get the update
        config firewall policy
            edit 1
                set ips-sensor sensor-11
                set application-list g-default
                set av-profile g-default
                set nat enable
            next
        end
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
        exe update-ips
        sleep 5
        exe update-now
        sleep 120
        #RestoreIPStftp /IPSEngine/v7.00/images/build0504/flen-fos7.4-7.504.pkg 172.18.52.254
        #sleep 60
        #y
        #sleep 10
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
        include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        config firewall policy
            edit 1
                unset ips-sensor
                unset application-list
                unset av-profile
                set nat disable
            next
        end
        include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt

    Parameters:
        fgt: FluentFortiGate device instance
    """
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt")
    if fgt.testbed.read_env_variables('FGT_A:VM') == 'yes':
        fgt.execute("config router static")
        fgt.execute("purge")
        fgt.execute("end")
    fgt.execute("config router static")
    fgt.execute("edit 1")
    fgt.execute("set device FGT_A:PORT1")
    fgt.execute("set gateway 172.16.200.254")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("get sys status")
    fgt.execute("setvar -e \"(?n)^Version: (.*?) v\" -to PLATFORM_TYPE")
    if fgt.testbed.read_env_variables('FGT_A:LOG_DEVICE') == 'memory':
        fgt.execute("config log memory filter")
        fgt.execute("set severity information")
        fgt.execute("end")
    else:
        fgt.execute("config log disk setting")
        fgt.execute("set status enable")
        fgt.execute("end")
    fgt.execute("config log memory setting")
    fgt.execute("set status enable")
    fgt.execute("end")
    fgt.execute("config log setting")
    fgt.execute("set local-out disable")
    fgt.execute("end")
    fgt.execute("config firewall address")
    fgt.execute("edit all")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config firewall ssl-ssh-profile")
    fgt.execute("edit \"new-deep-inspection\"")
    fgt.execute("config https")
    fgt.execute("set ports 443")
    fgt.execute("end")
    fgt.execute("config ftps")
    fgt.execute("set ports 990")
    fgt.execute("end")
    fgt.execute("config imaps")
    fgt.execute("set ports 993")
    fgt.execute("end")
    fgt.execute("config pop3s")
    fgt.execute("set ports 995")
    fgt.execute("end")
    fgt.execute("config smtps")
    fgt.execute("set ports 465")
    fgt.execute("end")
    fgt.execute("config ssl-exempt")
    fgt.execute("purge")
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
    fgt.execute("set nat disable")
    fgt.execute("set utm-status enable")
    fgt.execute("set profile-type single")
    fgt.execute("set profile-protocol-options \"default\"")
    fgt.execute("set ssl-ssh-profile \"new-deep-inspection\"")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set srcintf FGT_A:PORT1")
    fgt.execute("set dstintf FGT_A:PORT2")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("set nat disable")
    fgt.execute("set utm-status enable")
    fgt.execute("set profile-type single")
    fgt.execute("set profile-protocol-options \"default\"")
    fgt.execute("set ssl-ssh-profile \"new-deep-inspection\"")
    fgt.execute("next")
    fgt.execute("edit 3")
    fgt.execute("set srcintf vlan100")
    fgt.execute("set dstintf FGT_A:PORT1")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("set nat disable")
    fgt.execute("set utm-status enable")
    fgt.execute("set profile-type single")
    fgt.execute("set profile-protocol-options \"default\"")
    fgt.execute("set ssl-ssh-profile \"new-deep-inspection\"")
    fgt.execute("next")
    fgt.execute("edit 4")
    fgt.execute("set srcintf FGT_A:PORT1")
    fgt.execute("set dstintf \"vlan100\"")
    fgt.execute("set srcaddr \"all\"")
    fgt.execute("set dstaddr \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("set nat disable")
    fgt.execute("set utm-status enable")
    fgt.execute("set profile-type single")
    fgt.execute("set profile-protocol-options \"default\"")
    fgt.execute("set ssl-ssh-profile \"new-deep-inspection\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config firewall address6")
    fgt.execute("edit \"all\"")
    fgt.execute("next")
    fgt.execute("edit \"add6-1\"")
    fgt.execute("set ip6 2000:10:1:100::22/128")
    fgt.execute("next")
    fgt.execute("edit \"add6-2\"")
    fgt.execute("set ip6 2000:172:16:200::/64")
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
    fgt.execute("set utm-status enable")
    fgt.execute("set profile-type single")
    fgt.execute("set profile-protocol-options \"default\"")
    fgt.execute("set ssl-ssh-profile \"new-deep-inspection\"")
    fgt.execute("next")
    fgt.execute("edit 12")
    fgt.execute("set srcintf FGT_A:PORT1")
    fgt.execute("set dstintf FGT_A:PORT2")
    fgt.execute("set srcaddr6 \"all\"")
    fgt.execute("set dstaddr6 \"all\"")
    fgt.execute("set action accept")
    fgt.execute("set schedule \"always\"")
    fgt.execute("set service \"ALL\"")
    fgt.execute("set utm-status enable")
    fgt.execute("set profile-type single")
    fgt.execute("set profile-protocol-options \"default\"")
    fgt.execute("set ssl-ssh-profile \"new-deep-inspection\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config dlp filepattern")
    fgt.execute("edit 3")
    fgt.execute("set name \"flow-dlp\"")
    fgt.execute("config entries")
    fgt.execute("edit \"Executable (exe)\"")
    fgt.execute("set filter-type type")
    fgt.execute("set file-type exe")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config dlp profile")
    fgt.execute("edit \"flow-dlp\"")
    fgt.execute("config rule")
    fgt.execute("edit 1")
    fgt.execute("set proto http-get http-post")
    fgt.execute("set filter-by none")
    fgt.execute("set file-type 3")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config application custom")
    fgt.execute("edit \"custom-app\"")
    fgt.execute("set comment \"this is one test app signature\"")
    fgt.execute("set signature \"F-SBID( --name \\\"test_custom\\\"; --vuln_id 9998; --attack_id 9652; --protocol tcp; --default_action pass; --tag set,Tag.xvpn.ProH.TCP.Set; --revision 3029; --app_cat 12; --technology 1; --pop High; --risk Medium; --severity info; --app Other; --os All; --status disable; --service HTTP; --flow from_server; --file_type PDF; )\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config application list")
    fgt.execute("edit \"app-list-11\"")
    fgt.execute("config entries")
    fgt.execute("edit 1")
    fgt.execute("set application 15832 31077 15886 15817 9998")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set action reset")
    fgt.execute("set application 18094 15879")
    fgt.execute("next")
    fgt.execute("edit 3")
    fgt.execute("set action pass")
    fgt.execute("set application 15896 16337")
    fgt.execute("set shaper \"guarantee-100kbps\"")
    fgt.execute("set shaper-reverse \"guarantee-100kbps\"")
    fgt.execute("next")
    fgt.execute("edit 4")
    fgt.execute("set action pass")
    fgt.execute("set application 24818")
    fgt.execute("next")
    fgt.execute("edit 5")
    fgt.execute("set category 2")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config ips custom")
    fgt.execute("edit \"Heartbeat.Signature\"")
    fgt.execute("set comment ''")
    fgt.execute("set signature \"F-SBID( --attack_id 9999; --name Heartbeat.Signature; --revision 1; --protocol tcp; --tcp_flags S; --flow from_client; --src_addr [216.54.170.245, 10.1.100.11]; --dst_port 22; --default_action pass;)\"")
    fgt.execute("next")
    fgt.execute("edit \"test\"")
    fgt.execute("set comment ''")
    fgt.execute("set signature \"F-SBID( --name \\\"test\\\"; --attack_id 6406; --tag set,Tag.xvpn.ProH.TCP.Set; --severity low; --protocol tcp; --pattern \\\"ABCDEFG\\\";)\"")
    fgt.execute("next")
    fgt.execute("edit \"match small\"")
    fgt.execute("set comment ''")
    fgt.execute("set signature \"F-SBID( --attack_id 5835;  --name \\\"match small\\\"; --default_action pass; --service http; --protocol tcp; --pattern \\\"small\\\"; --severity info; )\"")
    fgt.execute("next")
    fgt.execute("edit \"match Passive FTP\"")
    fgt.execute("set comment ''")
    fgt.execute("set signature \"F-SBID( --attack_id 5277;  --name \\\"match Passive FTP\\\";  --protocol tcp;  --src_port 21; --pattern \\\"Passive\\\"; --severity medium; --status disable;)\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config ips sensor")
    fgt.execute("edit \"sensor-11\"")
    fgt.execute("config entries")
    fgt.execute("edit 1")
    fgt.execute("set action block")
    fgt.execute("set log-packet enable")
    fgt.execute("set rule 29844")
    fgt.execute("set status enable")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set action reset")
    fgt.execute("set log-packet enable")
    fgt.execute("set rule 5835")
    fgt.execute("set status enable")
    fgt.execute("next")
    fgt.execute("edit 3")
    fgt.execute("set action block")
    fgt.execute("set log-packet enable")
    fgt.execute("set quarantine attacker")
    fgt.execute("set rule 12705")
    fgt.execute("set status enable")
    fgt.execute("next")
    fgt.execute("edit 4")
    fgt.execute("set action pass")
    fgt.execute("set log-packet enable")
    fgt.execute("set rule 109445125")
    fgt.execute("set status enable")
    fgt.execute("next")
    fgt.execute("edit 5")
    fgt.execute("set application Sun")
    fgt.execute("set location client")
    fgt.execute("set os Windows")
    fgt.execute("set protocol HTTP")
    fgt.execute("set severity high critical")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config application list")
    fgt.execute("edit \"im_app\"")
    fgt.execute("config entries")
    fgt.execute("edit 1")
    fgt.execute("set application 16784 11203 16640 11580 16073 16783 108855300 14576 16538")
    fgt.execute("set session-ttl 200")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config antivirus profile")
    fgt.execute("edit \"AV-flow\"")
    fgt.execute("set comment \"flow-based scan and delete virus\"")
    fgt.execute("config http")
    fgt.execute("set av-scan block")
    fgt.execute("end")
    fgt.execute("config ftp")
    fgt.execute("set av-scan block")
    fgt.execute("end")
    fgt.execute("config imap")
    fgt.execute("set av-scan block")
    fgt.execute("end")
    fgt.execute("config pop3")
    fgt.execute("set av-scan block")
    fgt.execute("end")
    fgt.execute("config smtp")
    fgt.execute("set av-scan block")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config webfilter urlfilter")
    fgt.execute("edit 1")
    fgt.execute("set name \"web-filter-flow\"")
    fgt.execute("config entries")
    fgt.execute("edit 1")
    fgt.execute("set url \"www.apple.com\"")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set url \"ControlPC.qa.fortinet.com\"")
    fgt.execute("set action monitor")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config webfilter profile")
    fgt.execute("edit \"web-filter-flow\"")
    fgt.execute("set comment \"Flow-based web filter profile.\"")
    fgt.execute("config override")
    fgt.execute("set ovrd-user-group \"\"")
    fgt.execute("end")
    fgt.execute("config web")
    fgt.execute("set urlfilter-table 1")
    fgt.execute("end")
    fgt.execute("config ftgd-wf")
    fgt.execute("unset options")
    fgt.execute("config filters")
    fgt.execute("edit 6")
    fgt.execute("set category 12")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set category 7")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 4")
    fgt.execute("set category 9")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 14")
    fgt.execute("set category 64")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 1")
    fgt.execute("set category 2")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 9")
    fgt.execute("set category 15")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 5")
    fgt.execute("set category 11")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 16")
    fgt.execute("set category 66")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 12")
    fgt.execute("set category 57")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 7")
    fgt.execute("set category 13")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 3")
    fgt.execute("set category 8")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 8")
    fgt.execute("set category 14")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 13")
    fgt.execute("set category 63")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 17")
    fgt.execute("set category 67")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 15")
    fgt.execute("set category 65")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 10")
    fgt.execute("set category 16")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 18")
    fgt.execute("set category 26")
    fgt.execute("set action block")
    fgt.execute("next")
    fgt.execute("edit 11")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("end")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config emailfilter block-allow-list")
    fgt.execute("edit 1")
    fgt.execute("config entries")
    fgt.execute("edit 1")
    fgt.execute("set ip4-subnet 172.16.200.0 255.255.255.0")
    fgt.execute("next")
    fgt.execute("edit 2")
    fgt.execute("set type email-from")
    fgt.execute("set pattern \"tester@ControlPC.qa.fortinet.com\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("set name \"flow-spam\"")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config emailfilter profile")
    fgt.execute("edit \"flow-spam\"")
    fgt.execute("set spam-filtering enable")
    fgt.execute("set options spambal")
    fgt.execute("set spam-bal-table 1")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("config ips settings")
    fgt.execute("set proxy-inline-ips disable")
    fgt.execute("end")
    fgt.execute("diag sys session clear")
    fgt.execute("sleep 5")
    fgt.execute("diag de crashlog clear")
    fgt.execute("sleep 5")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/goroot.txt")
    fgt.execute("config firewall address")
    fgt.execute("edit all")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt")
    fgt.execute("config firewall policy")
    fgt.execute("edit 1")
    fgt.execute("set ips-sensor sensor-11")
    fgt.execute("set application-list g-default")
    fgt.execute("set av-profile g-default")
    fgt.execute("set nat enable")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt")
    fgt.execute("exe update-ips")
    fgt.execute("sleep 5")
    fgt.execute("exe update-now")
    fgt.execute("sleep 120")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt")
    fgt.execute("config firewall policy")
    fgt.execute("edit 1")
    fgt.execute("unset ips-sensor")
    fgt.execute("unset application-list")
    fgt.execute("unset av-profile")
    fgt.execute("set nat disable")
    fgt.execute("next")
    fgt.execute("end")
    fgt.execute("include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt")
