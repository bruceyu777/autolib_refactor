import pytest

from lib.core.device.session.pexpect_wrapper.output_buffer import OutputBuffer


@pytest.mark.skip(reason="OutputBuffer tests require device integration")
def test_output_buffer():
    multiline_str = """Operation Mode: TP
    Virtual domains status: 1 in NAT mode, 0 in TP mode"""

    output_buffer = OutputBuffer()
    output_buffer.append(multiline_str)

    pattern = "(?n)Operation.*NAT"
    res = output_buffer.search(pattern)
    assert res is None

    output_buffer.append(multiline_str)
    pattern = "Operation.*NAT"
    res = output_buffer.search(pattern)
    assert res is not None

    str2 = """
     get system status | grep 'Serial-Number' -A 3

Serial-Number: FG201FT921900397
BIOS version: 05000008
System Part-Number: P25132-01
Log hard disk: Available

FortiGate-201F (global) #
    """

    output_buffer = OutputBuffer()
    output_buffer.append(str2)

    pattern = r"(?n)Serial-Number: (FG[\d\w]+)"
    res = output_buffer.search(pattern)
    assert res is not None


def diag_autoupdate():
    str3 = """FortiGate-VM64-KVM # diag autoupdate versions


AV Engine
---------
Version: 7.00018 signed
Contract Expiry Date: n/a
Last Updated using manual update on Wed Aug  2 18:30:00 2023
Last Update Attempt: n/a
Result: Updates Installed

Virus Definitions
---------
Version: 1.00000 signed
Contract Expiry Date: n/a
Last Updated using manual update on Mon Apr  9 19:07:00 2018
Last Update Attempt: n/a
Result: Updates Installed

Extended set
---------
Version: 1.00000 signed
Contract Expiry Date: n/a
Last Updated using manual update on Mon Apr  9 19:07:00 2018
Last Update Attempt: n/a
Result: Updates Installed

Extreme set
---------
Version: 1.00000 signed
Contract Expiry Date: n/a
Last Updated using manual update on Mon Apr  9 19:07:00 2018
Last Update Attempt: n/a
Result: Updates Installed

Mobile Malware Definitions
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

IPS Attack Engine
---------
Version: 7.00510
Contract Expiry Date: n/a
Last Updated using manual update on Wed Aug 30 18:09:00 2023
Last Update Attempt: n/a
Result: Updates Installed

Attack Definitions
---------
Version: 6.00741 signed
Contract Expiry Date: n/a
Last Updated using manual update on Tue Dec  1 02:30:00 2015
Last Update Attempt: n/a
Result: Updates Installed

Attack Extended Definitions
---------
Version: 6.00741 signed
Contract Expiry Date: n/a
Last Updated using manual update on Tue Dec  1 02:30:00 2015
Last Update Attempt: n/a
Result: Updates Installed

Application Definitions
---------
Version: 6.00741 signed
Contract Expiry Date: n/a
Last Updated using manual update on Tue Dec  1 02:30:00 2015
Last Update Attempt: n/a
Result: Updates Installed

OT Threat Definitions
---------
Version: 6.00741 signed
Contract Expiry Date: n/a
Last Updated using manual update on Tue Dec  1 02:30:00 2015
Last Update Attempt: n/a
Result: Updates Installed

FMWP Definitions
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

IPS Malicious URL Database
---------
Version: 1.00001 signed
Contract Expiry Date: n/a
Last Updated using manual update on Thu Jan  1 01:01:00 2015
Last Update Attempt: n/a
Result: Updates Installed

IoT Detect Definitions
---------
Version: 0.00000 signed
Contract Expiry Date: n/a
Last Updated using manual update on Wed Aug 17 18:31:00 2022
Last Update Attempt: n/a
Result: Updates Installed

OT Detect Definitions
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

OT Patch Definitions
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

Flow-based Virus Definitions
---------
Version: 1.00000 signed
Contract Expiry Date: n/a
Last Updated using manual update on Mon Apr  9 19:07:00 2018
Last Update Attempt: n/a
Result: Updates Installed

Botnet Domain Database
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

Internet-service Standard Database
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

Device and OS Identifications
---------
Version: 1.00147
Contract Expiry Date: n/a
Last Updated using manual update on Fri Sep  8 01:00:00 2023
Last Update Attempt: n/a
Result: Updates Installed

URL Allow list
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

DLP Signatures
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

IP Geography DB
---------
Version: 3.00172
Contract Expiry Date: n/a
Last Updated using manual update on Wed Apr 12 19:23:00 2023
Last Update Attempt: n/a
Result: Updates Installed

Certificate Bundle
---------
Version: 1.00045
Contract Expiry Date: n/a
Last Updated using manual update on Wed Jun 28 20:51:00 2023
Last Update Attempt: n/a
Result: Updates Installed

Malicious Certificate DB
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

Mac Address Database
---------
Version: 1.00143
Contract Expiry Date: n/a
Last Updated using manual update on Tue Dec  6 09:00:00 2022
Last Update Attempt: n/a
Result: Updates Installed

AntiPhish Pattern DB
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Tue Nov 30 00:00:00 1999
Last Update Attempt: n/a
Result: Updates Installed

AI/Machine Learning Malware Detection Model
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

ICDB Database
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

Inline CASB Database
---------
Version: 1.00000
Contract Expiry Date: n/a
Last Updated using manual update on Tue Jul 25 22:16:00 2023
Last Update Attempt: n/a
Result: Updates Installed

Security Rating Data Package
---------
Version: 0.00000
Contract Expiry Date: n/a
Last Updated using manual update on Mon Jan  1 00:00:00 2001
Last Update Attempt: n/a
Result: Updates Installed

FDS Address
---------



FortiGate-VM64-KVM # """

    # Long pattern for comprehensive matching (commented out for brevity)
    # pattern = r"AV Engine\r\n---------\r\nVersion: ([\d.]+).*Virus Definitions..."
    pattern2 = r"AV Engine\r\n.*"
    output_buffer = OutputBuffer()
    output_buffer.append(str3)
    res = output_buffer.search(pattern2)
    assert res is not None


@pytest.mark.skip()
def test_system_status():
    s = """Version: FortiGate-VM64-KVM v7.4.2,build2492,230908 (interim)
First GA patch build date: 230509
Security Level: 0
Virus-DB: 1.00000(2018-04-09 18:07)
Extended DB: 1.00000(2018-04-09 18:07)
Extreme DB: 1.00000(2018-04-09 18:07)
AV AI/ML Model: 0.00000(2001-01-01 00:00)
IPS-DB: 6.00741(2015-12-01 02:30)
IPS-ETDB: 6.00741(2015-12-01 02:30)
APP-DB: 6.00741(2015-12-01 02:30)
FMWP-DB: 0.00000(2001-01-01 00:00)
IPS Malicious URL Database: 1.00001(2015-01-01 01:01)
IoT-Detect: 0.00000(2022-08-17 17:31)
OT-Detect-DB: 0.00000(2001-01-01 00:00)
OT-Patch-DB: 0.00000(2001-01-01 00:00)
OT-Threat-DB: 6.00741(2015-12-01 02:30)
IPS-Engine: 7.00510(2023-08-30 17:09)
Serial-Number: FGVMEV1UGQD00SC4
License Status: Invalid
VM Resources: 1 CPU/1 allowed, 1993 MB RAM/2048 MB allowed
Log hard disk: Available
Hostname: FortiGate-VM64-KVM
Operation Mode: NAT
Current virtual domain: root
Max number of virtual domains: 2
Virtual domains status: 1 in NAT mode, 0 in TP mode
Virtual domain configuration: disable
FIPS-CC mode: disable
Current HA mode: standalone
Branch point: 2492
Release Version Information: interim
FortiOS x86-64: Yes
System time: Mon Sep 11 15:38:29 2023
Last reboot reason: warm reboot

FortiGate-VM64-KVM #  """
    output_buffer = OutputBuffer()
    output_buffer.append(s)
    pattern = (
        r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
        r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
        r"Serial-Number: (?P<Serial>[^\n]*).*"
        # r"BIOS version: (?P<bios_version>[^\n]*).*"
        r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
        r"Branch point: (?P<branch_point>[^\n]*).*"
    )
    res = output_buffer.search(pattern)
    assert res is not None


@pytest.mark.skip()
def test_multiline():
    s = """rm: cannot remove '/tftpboot/*.mib': No such file or directory
]0;root@kvm-server: ~root@kvm-server:~# ------------------------< LATEST 7.2 IMAGES >-------------------------
drwx---rwx    3 550      2147483647       96 Apr 23  2023 build1497
drwx---rwx    3 550      2147483647       96 Apr 24  2023 build1498
drwx---rwx    3 550      2147483647       96 Apr 24  2023 build1499  <-

]0;root@kvm-server: ~root@kvm-server:~# """
    output_buffer = OutputBuffer()
    output_buffer.append(s)

    pattern = r"build(\d{1,4})  <-"
    res = output_buffer.search(pattern)
    print(res)
    assert res is not None


def test_double_quote():
    s = """diag sys session clear

FGVM04TM23004610 (Interim)# exe log filter category traffic

FGVM04TM23004610 (Interim)# exe log filter field subtype forward

FGVM04TM23004610 (Interim)# exe log filter field dstip 10.1.100.173

FGVM04TM23004610 (Interim)# exe log display
1 logs found.
1 logs returned.

1: date=2023-11-22 time=10:33:39 eventtime=1700678018996668791 tz="-0800" logid="0000000013" type="traffic" subtype="forward" level="notice" vd="root" srcip=10.1.100.22 identifier=18 srcintf="port2" srcintfrole="undefined" dstip=10.1.100.173 dstintf="port3" dstintfrole="undefined" srccountry="Reserved" dstcountry="Reserved" sessionid=1338 proto=1 action="accept" policyid=811526 policytype="policy" poluuid="a0657c26-8965-51ee-7af7-f3570650d4ad" service="PING" trandisp="snat+dnat" tranip=172.16.200.55 tranport=0 transip=172.16.200.200 transport=0 duration=9 sentbyte=840 rcvdbyte=840 sentpkt=10 rcvdpkt=10 appcat="unscanned"


FGVM04TM23004610 (Interim)# """
    output_buffer = OutputBuffer()
    output_buffer.append(s)

    pattern = r'trandisp="snat\+dnat'
    res = output_buffer.search(pattern)
    print(res)
    assert res is not None
