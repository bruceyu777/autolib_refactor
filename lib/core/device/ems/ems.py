import json
import os
import time
import xml.etree.ElementTree as ET

import requests
import urllib3

from lib.core.device._helper.common import (
    TransformedDict,
    extract_key,
    pprint_http_request,
    url_check,
)
from lib.services.log import logger
from lib.utilities.exceptions import ResourceNotAvailable

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_RETRY = urllib3.Retry(
    total=3,
    read=3,
    connect=3,
    backoff_factor=0.3,
    status_forcelist=[429, 500, 502, 503, 504],
)


class Meta(TransformedDict):
    def verify_field(self, value, schema):
        type_mapping = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "object": object,
            "array": list,
        }
        expected_type = type_mapping.get(schema["type"], object)
        check_result = isinstance(value, expected_type)
        return check_result and value in schema.get("enum", [value])

    def verify_parameters(self, session, kwargs):
        required_fields = (f for f in self["parameters"] if f.get("required", False))
        for field in required_fields:
            mapping = {"header": session.headers, "cookie": session.cookies}
            value = mapping.get(field["in"], kwargs).get(field["name"], None)
            if not self.verify_field(value, field["schema"]):
                return False
        return True


class API:
    def __init__(self, url, metadata, host, port=443, protocol="https"):
        self.host = host
        self.protocol = protocol
        self._url_prefix = "{}://{}:{}".format(self.protocol, self.host, port)
        self._url_tail = url
        self._url = None
        self._apis = {method: Meta(data) for method, data in metadata.items()}

    def _prepare_url(self, parameters):
        if self._url is None:
            url = self._url_tail.format(**parameters)
            if not url.startswith(self._url_prefix):
                url = url_check(self._url_prefix, url)
            self._url = url
        return self._url

    def _update_headers(self, session):
        session.headers.update(
            {
                "Referer": "{}/installer_form".format(self._url_prefix),
                "Host": self.host,
                "Origin": self._url_prefix,
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    " (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"
                ),
            }
        )
        if "csrftoken" in session.cookies:
            session.headers["X-CSRFToken"] = str(session.cookies["csrftoken"])
        session.headers["Ems-Call-Type"] = "2"

    def _update_parameters(self, parameters):
        logger.debug(">>> parameters: %s", parameters)
        if "verify" not in parameters:
            parameters["verify"] = False
        return parameters

    def __call__(self, session, method, param=None):
        if method not in self._apis:
            raise NotImplementedError(
                f"Method({method}) not supported for {self._url_tail}"
            )

        param = param or {}
        url_params = {
            k: v for k, v in param.items() if k in extract_key(self._url_tail)
        }
        url = self._prepare_url(url_params)
        updated_params = {k: v for k, v in param.items() if k not in url_params}
        parameters = self._update_parameters(updated_params)
        self._update_headers(session)
        return self._request(session, url, method, parameters)

    def _request(self, session, url, method, kwargs):
        function = getattr(session, method)
        if not callable(function):
            raise ResourceNotAvailable(f"Invalid method({method})!")
        response = function(url, **kwargs)
        pprint_http_request(response)
        return response


class APIManager:
    def __init__(self, version, host, port=443, protocol="https", sase=False):
        self.home_dir = os.path.join(os.path.dirname(__file__), "metadata")
        self.version = version
        self.files = self._discover_files(sase)
        self.metadata = self._load_metadata()
        self.apis = self._load_apis(host, port, protocol)
        self.host = host

    def _discover_files(self, sase):
        return [
            f
            for f in os.listdir(self.home_dir)
            if f.endswith(".json") and ("sase" in f) == sase
        ]

    def _load_apis(self, host, port, protocol):
        return {
            url: API(url, meta, host, port, protocol)
            for url, meta in self.metadata["paths"].items()
        }

    @property
    def version_inline(self):
        return self.metadata.get("info", {}).get("version", "")

    @property
    def server_url(self):
        return self.metadata.get("servers", [{}])[0].get(
            "url", "https://{address}:{port}"
        )

    def _load_metadata(self):
        selected_files = [
            filename for filename in self.files if filename.startswith(self.version)
        ]
        if not selected_files:
            raise ResourceNotAvailable(
                f"No metadata file found for version {self.version}"
            )
        with open(
            os.path.join(self.home_dir, selected_files[0]), encoding="utf-8"
        ) as f:
            return json.load(f)

    def __call__(self, url, session, method, parameters):
        if url not in self.apis:
            raise NotImplementedError("Unsupported API: %s" % url)
        return self.apis[url](session, method, parameters)


# TODO: more customize needs to be supported or fixed
class EMS:

    COMPONENT_MAPPING = {
        "malware": "1",
        "sandbox": "2",
        "webfilter": "3",
        "firewall": "4",
        "vpn": "5",
        "vulnerability_scan": "6",
        "system": "7",
    }

    def __init__(self, config, alias):
        self.config = config
        self.alias = alias
        self._session = None
        self.api_caller = self._init_api_caller()
        self.authorized = False
        self.version = ""
        self.access_protocol = self.config.get("ACCESS_PROTOCOL", "https")
        self.connection = self.config.get("CONNECTION", "")
        self.username = self.config.get("USERNAME", "")
        self.password = self.config.get("PASSWORD", "")
        self.dynamic_variables = self.config.get("dynamic_variables", {})

    def _init_api_caller(self):
        host, *extra_info = self.connection.split()
        return APIManager(
            self.version,
            host,
            int(extra_info[0]) if extra_info else 443,
            self.access_protocol,
            sase=self.config.is_flag_enabled(self.alias, "sase"),
        )

    def __del__(self):
        if self._session:
            self._session.close()
            self._session = None

    def authorization(self):
        response = self.api_caller(
            "/api/v1/auth/signin",
            self.session,
            "post",
            {
                "json": {
                    "name": self.username,
                    "password": self.password,
                }
            },
        )
        self.authorized = response.ok

    def call(self, method, url, params=None):
        if not self.authorized:
            self.authorization()
        response = self.api_caller(url, self.session, method, params)
        self.authorized = response.state_code != 401
        if not self.authorized:
            self._session.close()
            logger.debug("Unauthorized, close session!")
        return response

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(max_retries=DEFAULT_RETRY)
            self._session.mount(self.access_protocol, adapter)
        return self._session

    def authorize_fabric_device(self, device_certificate_id, authorize=True):
        url = "/api/v1/client_certificates/{}/set".format(device_certificate_id)
        response = self.call("patch", url, {"json": {"authorized": authorize}})
        if not response.ok:
            raise ResourceNotAvailable("Failed to authorize required device!")

    def delete_fabric_device(self, device_certificate_id):
        url = "/api/v1/client_certificates/{}/delete".format(device_certificate_id)
        return self.call("delete", url)

    def authorize_fabric_device_by_sn(self, sn, authorize=True, retry=5, interval=10):
        while retry:
            response = self.call("get", "/api/v1/client_certificates/index")
            data = response.json().get("data", [])
            device_ids = [i["id"] for i in data if i["cn"] == sn]
            if device_ids:
                return self.authorize_fabric_device(device_ids[0], authorize=authorize)
            retry -= 1
            time.sleep(interval)
        raise ResourceNotAvailable("Unable to find required sn in EMS: %s" % sn)

    def get_license_generator_cmd(self):
        return "LicenseGenerator.exe -f license.lic -u {uid} -s {sn} -a {licenses}"

    def get_sys_info(self):
        response = self.call("get", "/api/v1/system/info")
        return json.loads(response.content)["data"]

    def get_list_of_endpoints(self):
        response = self.call(
            "get", "/api/v1/endpoints/index", {"params": {"count": 2000}}
        )
        data = json.loads(response.content)
        endpoints = data.get("data", {}).get("endpoints", {})
        return endpoints

    def endpoint_details(self, device_id):
        response = self.call(
            "get", "/api/v1/endpoints/{device_id}/get", {"device_id": device_id}
        )
        return json.loads(response.content).get("data", {})

    def get_endpoint(self, **filters):
        endpoints = self.get_list_of_endpoints()
        if filters and endpoints:
            for endpoint in endpoints:
                if all(endpoint.get(k, "") == v for k, v in filters.items()):
                    return endpoint
        return endpoints

    def get_endpoint_status(self, device_id):
        endpoint = self.get_endpoint(device_id=device_id)

        line_status = None
        if "is_ems_online" in endpoint and "last_seen" in endpoint:
            line_status = int((time.time() - endpoint["last_seen"]) <= 35)

        status = {
            "net_status": endpoint.get("is_ems_onnet"),
            "registered": endpoint.get("is_registered"),
            "line_status": line_status,
        }

        if any(value is None for value in status.values()):
            logger.exception("Getting EMS endpoint status")

        return status

    def delete_device(self, device_id):
        url = "/api/v1/devices/delete"
        params = {"ids": device_id}
        return self.call("delete", url, params=params)

    def get_device_id(self, serial):
        endpoints = self.get_list_of_endpoints()
        device_ids = {
            endpoint["fct_sn"]: endpoint["device_id"] for endpoint in endpoints
        }
        device_id = device_ids.get(serial, None)
        logger.debug("device_id: %s", device_id)
        return device_id

    def get_device_ids_by_ip(self, ip_addr):
        endpoints = self.get_list_of_endpoints()
        return [
            endpoint["device_id"]
            for endpoint in endpoints
            if endpoint["ip_addr"] == ip_addr
        ]

    def create_group(self, group_name):
        response = self.call(
            "get",
            "/api/v1/workgroups/create",
            params={"name": group_name, "parent_id": 1},
        )
        return response.content

    def get_list_of_groups(self):
        response = self.call("get", "/api/v1/workgroups/index")
        return json.loads(response.content)["data"]

    def get_group_by_vm(self, vm_name):
        groups = self.get_list_of_groups()
        for group in groups:
            if group["name"] == vm_name:
                return group
        return None

    def move_to_group(self, device_id, group_id):
        url = "/api/v1/workgroups/move/"
        response = self.call(
            "get", url, params={"id_list": device_id, "group_id": group_id}
        )
        return response

    def get_profile_list(self):
        url = "/api/v1/profiles/index/?call_type=2"
        response = self.call("get", url)
        try:
            return json.loads(response.content)["data"][0]["profiles"]
        except (json.JSONDecodeError, KeyError, IndexError):
            logger.exception("Unable to retrieve profile list")
        return None

    def get_profile(self, profile_id):
        url_template = "/api/v1/profiles/get/?is_chrome=false&id={}&call_type=2"
        response = self.call("get", url_template.format(profile_id))
        try:
            return json.loads(response.content)["data"]
        except (json.JSONDecodeError, KeyError):
            logger.exception("Unable to retrieve profile")
        return None

    def get_default_profile(self):
        url = "/api/v1/profiles/get/?is_chrome=false&call_type=2"
        response = self.call("get", url)
        try:
            return json.loads(response.content)["data"]
        except (json.JSONDecodeError, KeyError):
            logger.exception("Unable to retrieve profile")
        return None

    def get_default_profile_filepath(self):
        default_profile = self.get_default_profile()
        prof_file_path = os.path.join(
            self.dynamic_variables["local_base_folder"], "default_profile.conf"
        )
        with open(prof_file_path, "w", encoding="utf-8") as f:
            if default_profile:
                f.write(default_profile["xml"])
        return prof_file_path

    def get_clean_profile_filepath(self):
        return self.dynamic_variables["fct_default_cfg"]

    def set_profile(self, profile_id, name, config):
        data = {
            "id": profile_id,
            "name": name,
            "config": json.dumps(config),
            "call_type": 2,
        }
        response = self.call("post", "/api/v1/profiles/set/ui", params=data)
        return json.loads(response.content)

    def import_profile_xml(self, profile, xml, component):
        tree = ET.parse(xml)
        root = tree.getroot()
        xml_str = ET.tostring(root, encoding="unicode", method="xml")
        data = {
            "name": profile,
            "xml": xml_str,
            "components": self.COMPONENT_MAPPING[component],
            "profile_component_id": 1,
        }
        response = self.call("post", "/api/v1/profiles/import/xml", data)
        return json.loads(response.content)

    def revoke_ems_ztna_cert(self):
        url = "/api/v1/ztna_certificates/revoke"
        response = self.call("post", url)
        return json.loads(response.content)

    def send_one_way_message(self, msg_type, uuids, send_content):
        url = "/api/v1/clients/send_message"
        field_key = "content" if msg_type == "plain" else "content_file_name"
        params = {
            "data": {
                "message_type": msg_type,
                "client_uuids": uuids,
                field_key: send_content,
            },
            "files": {field_key: send_content},
        }
        response = self.call("post", url, params=params)
        return json.loads(response.content)

    def get_serial(self):
        url = "/api/v1/system/serial_number"
        response = self.call("get", url)
        return json.loads(response.content)["data"]

    def update_password(self, ems_pass, ems_user):
        url = "/api/v1/admins/set/password"
        data = {"old": "", "new": ems_pass, "username": ems_user}
        return self.call("post", url=url, params=data)

    def get_server_settings(self):
        url = "/api/v1/settings/get/server"
        resp = self.call("get", url)
        return json.loads(resp.content)["data"]

    def deregister_fct(self, device_id):
        url = '/api/v1/clients/deregister?ids=["{}"]'.format(device_id)
        response = self.call("get", url)
        return response

    def revoke_client_cert(self, device_ids: list):
        url = "/api/v1/clients/revoke_cert"
        params = {
            "json": {"client_ids": device_ids},
        }
        response = self.call("post", url, params)
        logger.info("update profile: %s", response)
        return json.loads(response.content)
