import re

from lib.services import logger

from .fos_dev import FosDev


def parse_version(version):
    pattern = re.compile(
        r"^v(?P<version>\d+\.\d+\.\d+)-build((?P<build>\d+)) \d+\((?P<release_type>.*?)\)"
    )
    matched = pattern.search(version)
    return matched.groupdict() if matched else {}


class FAZ(FosDev):

    @property
    def system_status(self):
        """
        parse return from 'get system status' to get:
        1> version, branch point
        2> serial number
        3> BIOS
        FAZVM64 # get system status
        Platform Type                   : FAZVM64
        Platform Full Name              : FortiAnalyzer-VM64
        Version                         : v6.0.1-build0150 180606 (GA)
        Serial Number                   : FLULVM0000006534
        BIOS version                    : 04000002
        Hostname                        : FAZVM64
        Max Number of Admin Domains     : 10000
        Admin Domain Configuration      : Disabled
        Branch Point                    : 0150
        Release Version Information     : GA
        Current Time                    : Tue Aug 07 08:58:54 PDT 2018
        Daylight Time Saving            : Yes
        Time Zone                       : (GMT-8:00) Pacific Time (US & Canada).
        x86-64 Applications             : Yes
        Disk Usage                      : Free 65.06GB, Total 78.62GB
        File System                     : Ext4
        License Status                  : Valid
        """
        *_, system_info_raw = self.send_command(
            "get system status", pattern="Release Version.*?# $", timeout=10
        )
        selected_lines = [
            l.split(": ", maxsplit=1) for l in system_info_raw.splitlines() if ": " in l
        ]
        if not selected_lines:
            return {}
        system_status = {k.strip(): v.strip() for (k, v) in selected_lines}
        if "Version" in system_status:
            system_status.update(parse_version(system_status["Version"]))
        if "BIOS version" not in system_status:
            system_status["BIOS version"] = "0"
        logger.debug("System status: %s", system_status)
        return system_status


class FMG(FAZ):
    """FMG and FAZ used same code at product side

    QA_FMG_V760_62 # get system status
    Platform Type                   : FMG-VM64-KVM
    Platform Full Name              : FortiManager-VM64-KVM
    Version                         : v7.6.0-build3340 240729 (GA.F)
    Serial Number                   : FMG-VMTM24008240
    BIOS version                    : 04000002
    Hostname                        : QA_FMG_V760_62
    Max Number of Admin Domains     : 10000
    Max Number of Device Groups     : 10000
    Admin Domain Configuration      : Enabled
    FIPS Mode                       : Disabled
    HA Mode                         : Stand Alone
    Branch Point                    : 3340
    Release Version Information     : GA.F
    Current Time                    : Wed Nov 13 15:32:43 PST 2024
    Daylight Time Saving            : Yes
    Time Zone                       : (GMT-8:00) Pacific Time (US & Canada).
    x86-64 Applications             : Yes
    Disk Usage                      : Free 74.54GB, Total 97.87GB
    File System                     : Ext4
    License Status                  : Valid
    Image Signature                 : Image is GA Certified
    """
