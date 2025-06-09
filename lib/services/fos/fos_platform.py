import csv
import json
from pathlib import Path

from lib.services.log import logger

PLATFORM_GEN_CSV_FILEPAHT = Path(__file__).resolve().parent / "static" / "pltrev.csv"


class FosPlatformManager:

    oriole_abbr_mapping = {
        "FortiGateRugged": "FGR",
        "FortiGate": "FGT",
        "FortiCarrier": "FGT",
        "FortiGateCarrier": "FGT",
        "FortiWiFi": "FWF",
        "FortiAP": "FAP",
        "FortiSwitch": "FSW",
        "FortiFirewall": "FFW",
        "FortiFirewallCarrier": "FFW",
    }

    def __init__(self, platform_revision_filepath=PLATFORM_GEN_CSV_FILEPAHT):
        self.platform_revision = self._load(platform_revision_filepath)

    def _load(self, filepath):
        with open(filepath) as f:
            f_csv = csv.DictReader(f)
            return {r["plt_name"]: r["rev"] for r in f_csv}

    @staticmethod
    def normailze_prefix(plt_prefix):
        return FosPlatformManager.oriole_abbr_mapping.get(plt_prefix, "")

    @staticmethod
    def platforms():
        return list(FosPlatformManager.oriole_abbr_mapping.keys())

    @staticmethod
    def normalize_platform(org_platform):
        model = org_platform.replace("-", "_")
        platform_prefix, *_ = model.split("_")
        normalized = FosPlatformManager.normailze_prefix(platform_prefix)
        if normalized:
            return model.replace(platform_prefix, normalized)
        if platform_prefix not in FosPlatformManager.oriole_abbr_mapping.values():
            msg = "Model is %s, not in known model list:\n%s\n"
            logger.error(msg, model, json.dumps(FosPlatformManager.platforms()))
        return org_platform

    def get_platform_generation(self, _platform):
        return self.platform_revision.get(_platform, "1")


platform_manager = FosPlatformManager()
