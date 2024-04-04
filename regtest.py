import regex
pattern = "Serial-Number: (.*?)\n"
# m = regex.match(r"^\(\?n\)(.*)", pattern)
s = """
FGT1801F_APP_A (vd1) (Interim)# get system status
Version: FortiGate-1801F v7.6.0,build3352,240417 (Beta 1.F)
First GA patch build date: 230509
Security Level: 1
Firmware Signature: certified
Virus-DB: 1.00000(2018-04-09 18:07)
Extended DB: 1.00000(2018-04-09 18:07)
Extreme DB: 1.00000(2018-04-09 18:07)
AV AI/ML Model: 0.00000(2001-01-01 00:00)
IPS-DB: 6.00741(2015-12-01 02:30)
IPS-ETDB: 6.00741(2015-12-01 02:30)
APP-DB: 27.00771(2024-04-18 00:23)
Proxy-IPS-DB: 6.00741(2015-12-01 02:30)
Proxy-IPS-ETDB: 6.00741(2015-12-01 02:30)
Proxy-APP-DB: 27.00771(2024-04-18 00:23)
FMWP-DB: 24.00020(2024-02-13 17:03)
IPS Malicious URL Database: 1.00001(2015-01-01 01:01)
IoT-Detect: 27.00771(2024-04-17 17:15)
OT-Detect-DB: 27.00771(2024-04-17 17:15)
OT-Patch-DB: 27.00765(2024-04-10 16:56)
OT-Threat-DB: 6.00741(2015-12-01 02:30)
IPS-Engine: 7.01002(2024-04-15 20:27)
Serial-Number: FG181FTK22901387
BIOS version: 05000012
System Part-Number: P25035-05
Log hard disk: Available
Hostname: FGT1801F_APP_A
Private Encryption: Disable
Operation Mode: NAT
Current virtual domain: vd1
Max number of virtual domains: 10
Virtual domains status: 2 in NAT mode, 0 in TP mode
Virtual domain configuration: multiple
FIPS-CC mode: disable
Current HA mode: standalone
Branch point: 3352
Release Version Information: Beta 1
FortiOS x86-64: Yes
System time: Thu Apr 18 09:43:21 2024
Last reboot reason: warm reboot"""


flag = regex.DOTALL | regex.MULTILINE
pattern = r'Serial-Number: (.*?)\n'
m = regex.match(r"^\(\?n\)(.*)", pattern)

# logger.info("The original pattern is: %s", pattern)
if m is not None:
    flag = regex.MULTILINE
    pattern = m.group(1)
# logger.info("The extracted pattern is: %s", pattern)
pattern = regex.compile(pattern, flag)

# pattern =regex.compile('Serial-Number: (.*?)\\n', regex.S | regex.M | regex.V0)
print(pattern)
m = regex.search(pattern, s)
# print(m.groups())
print(f"({m.group(1)})")
