import os

ORIOLE_REPORT_FOLDER = "."
SUMMARY_FILE_NAME_PREFIX = "AutoTesting_Oriole_"
FILE_EXT = ".json"


ORIOLE_SUBMIT_URL = r"http://172.16.100.117/wsqadb/AutoTestResult?wsdl"
PLATREV_CSV_FILE = "pltrev.csv"
CFG_FILE_DIR = os.path.dirname(os.path.realpath(__file__))
TEMPLATE_FILE_NAME = "summary.template"

ORIOLE_REPORT_FIXED_FIELDS = {
    "cidb": "1.00111",
    "avdb": "1.00000",
    "dbdb": "0.00000",
    "nids": "6.00741",
    "mmdb": "0.00000",
    "isdb": "6.00741",
    "flen": "7.00006",
    "total": "12",
    "aven": "6.00151",
    "apdb": "6.00741",
    "nids_ext": "6.00741",
    "ffdb": "0.00000",
    "mudb": "1.00001",
    "bios": "05000006",
    "ipge": "3.00041",
    "SN": "FG39E6T018900077",
    "crdb": "1.00021",
    "mcdb": "0.00000",
}

PRODUCT_SHORTEN = {
    "FortiGate-Rugged-": "FGR_",
    "FortiGate-": "FGT_",
    "FortiWiFi-": "FWF_",
    "FortiCarrier-": "FGT_",
    "FortiFirewall-": "FFW_",
    "FortiFirewallCarrier-": "FFW_",
}

HOST = "172.18.52.254"
PORT = "8090"
