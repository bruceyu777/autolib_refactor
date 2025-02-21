from lib.services.image_server import IMAGE_SERVER_FQDN

ORIOLE_REPORT_FOLDER = "."
SUMMARY_FILE_NAME_PREFIX = "AutoTesting_Oriole_"
FILE_EXT = ".json"
REPORT_FILE = "Oriole_report.json"

ORIOLE_SUBMIT_API_URL = f"https://{IMAGE_SERVER_FQDN}/api/oriole"

ORIOLE_REPORT_FIXED_FIELDS = {
    "cidb": "0.00000",
    "avdb": "0.00000",
    "dbdb": "0.00000",
    "nids": "0.00000",
    "mmdb": "0.00000",
    "isdb": "0.00000",
    "flen": "0.00000",
    "total": "1",
    "aven": "0.00000",
    "apdb": "0.00000",
    "nids_ext": "0.00000",
    "ffdb": "0.00000",
    "mudb": "0.00000",
    "bios": "00000000",
    "ipge": "0.00000",
    "SN": "FG39E6T018900077",
    "crdb": "0.00000",
    "mcdb": "0.00000",
}


ORIOLE_FIELD_FOS_SOURCE = {
    "apdb": ["Application Definitions"],
    "avdb": ["Virus Definitions"],
    "avdef": ["Virus Definitions", "Extended set", "Flow-based Virus Definitions"],
    "aven": ["AV Engine"],
    "bios": ["BIOS version"],
    "build": ["build"],
    "eavdf": ["Extended set"],
    "favdf": ["Flow-based Virus Definitions"],
    "flen": ["IPS Attack Engine"],
    "ipsdef": ["Attack Definitions", "Attack Extended Definitions"],
    "nids": ["Attack Definitions"],
    "nids_ext": ["Attack Extended Definitions"],
    "platform": ["platform"],
    "SN": ["Serial-Number"],
    "snmp_mib": ["build"],
}


ORIOLE_FIELD_FAP_SOURCE = {
    "fos": ["FortiOS"],  # 5.0.3.0123
    "fcld": ["FortiCloud"],  # 5.0.3.283498
    "aven": ["av engine"],
    "avdb": ["av db"],
    "bios": ["BIOS version"],
    "build": ["build"],
    "flen": ["ips engine"],
    "nids": ["ips db"],
    "ibdb": ["ips botnet db"],
    "platform": ["platform"],
    "SN": ["Serial-Number"],
    "snmp_mib": ["build"],
    "apdb": ["app db"],
}


ORIOLE_FIELD_SOURCE = {"FOS": ORIOLE_FIELD_FOS_SOURCE, "FAP": ORIOLE_FIELD_FAP_SOURCE}


ORIOLE_FIELD_MAPPING = {
    "AS DB Version": "asever",
    "AS Engine": "aseeng",
    "AV DB Version": "avdef",
    "AV Engine": "aven",
    "Application Definitions": "apdb",
    "BIOS": "bios",
    "Botnet DB": "ibdb",
    "Botnet DB Version": "botnetdef",
    "Botnet Definition": "ibdb",
    "Botnet Domain Database": "dbdb",
    "Browser-Chrome": "browser_gcr",
    "Browser-FF": "browser_ff",
    "Browser-IE": "browser_ie",
    "Browser-Safari": "browser_saf",
    "Build": "build",
    "Certificate Bundle": "crdb",
    "DUT serial number": "SN",
    "Device OS DB": "cidb",
    "EMS": "ems",
    "FAP": "fap",
    "FDN": "fdn",
    "FEXP": "fexp",
    "FEXP-Android": "fexp_droid",
    "FEXP-iOS": "fexp_ios",
    "FOS": "fos",
    "FSSO": "fsso",
    "FortiAP": "fap",
    "FortiAnalyzer": "faz",
    "FortiAuthenticator": "fac",
    "FortiClient-Android": "fct_droid",
    "FortiClient-ChromeOS": "fct_chrome",
    "FortiClient-Mac": "fct_mac",
    "FortiClient-Win": "fct",
    "FortiClient-iOS": "fct_ios",
    "FortiCloud": "fcld",
    "FortiExtender": "fext",
    "FortiManager": "fmg",
    "FortiOS": "fos",
    "FortiSASE Controller": "sase_controller",
    "FortiSASE SIA UI": "fsase_sia_ui",
    "FortiSandbox": "fsa",
    "FortiSwitch": "fsw",
    "FortiSwitchATCA": "ft",
    "FortiSwitchOS": "fsw",
    "IP Geography DB": "ipge",
    "IPS DB Version": "nids",
    "IPS Engine": "flen",
    "IPS Extended DB Version": "nids_ext",
    "IPS Malicious URL Database": "mudb",
    "Industrial Attack Definitions": "isdb",
    "Internet-service Database Apps": "ffdb",
    "Malicious Certificate Database": "mcdb",
    "Mobile Malware Definitions": "mmdb",
    "Platform": "platform_id",
    "Platform Generation": "pltgen",
    "SDNConnector": "sdnconn",
    "SDNS": "sdns",
    "SNMP-MIB": "snmp_mib",
    "SSL-VPN": "sslvpn",
    "Security Rating DB": "sfas",
    "URL White list": "uwdb",
    "VCM DB Version": "vcmver",
    "VCM Engine": "vcmeng",
    "VCM Plugin": "vcm_plugin",
    "VM DB Version": "vmver",
    "VM Engine": "vmeng",
}
