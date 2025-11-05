import pytest

from lib.services import oriole


@pytest.mark.skip(
    reason="Oriole reporting requires full environment and network access"
)
def test_oriole():
    dummy_device_info = {
        "platform": "FortiGate-81E",
        "version": "v7.0.0",
        "build": "build0113",
        "release_type": "GA",
        "serial": "FGT81ETK18003552",
        "bios_version": "05000007",
        "branch_point": "0066",
        "AV Engine": "6.00258",
        "Virus Definitions": "68.00873",
        "Extended set": "1.00000",
        "IPS Attack Engine": "7.00018",
        "Attack Definitions": "6.00741",
        "Attack Extended Definitions": "0.00000",
        "Application Definitions": "6.00741",
        "IPS Malicious URL Database": "1.00001",
        "Flow-based Virus Definitions": "1.00123",
        "Botnet Domain Database": "2.00253",
    }
    oriole.report(985331, False, dummy_device_info)
