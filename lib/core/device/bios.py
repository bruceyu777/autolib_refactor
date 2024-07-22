import re
import time


class BIOS:
    pattern = {
        "entry_point": r"to display configuration menu",
        "main_menu": r"Enter [CG].*?[HQ]:$",
        "wildcard_menu": r"Enter .*?[HQ]:$",
        "set_option": r"Enter.*?\[.*?\]:",
        "dhcp_option": r"Enter DHCP setting.*?:",
        "general_choice": r"\]\?",
        "firmware_choice": (r"Save as Default firmware.*?saving:\[D/B/R\]\?"),
        "format_boot_device": r"It will erase.*?Continue\? \[yes/no\]",
        "yes_or_no": r"\[Y/N\]\?$",
    }
    command = {
        "dummy": "",
        "Y": "Y",
        "yes": "yes",
        "quit": "Q",
        "help": "H",
        "set_vlan_id": "V",
        "set_dhcp_status": "D",
        "disable_dhcp": "2",
        "set_default_firmware": "D",
        "set_backup_firmware": "B",
        "set_local_gateway": "G",
        "goto_tftp_menu": "C",
        "diagnose_network": "N",
        "set_net_mask": "S",
        "set_security_level": "U",
        "reset_tftp_parameters": "E",
        "system_info": "I",
        "set_download_port": "P",
        "set_restrict_mode": "R",
        "set_firmware_filename": "F",
        "set_timeout": "T",
        "set_local_ip": "I",
        "review_tftp_settings": "R",
        "format_boot_device": "F",
        "set_tftp_server_ip": "T",
    }
