import json
import re
from collections.abc import MutableMapping
from string import Formatter

import requests

from lib.services import logger

BURN_IMAGE_STAGE = "BURN_IMAGE"
LOGIN_STAGE = "LOGIN"
HD_TITLE = "\n------- Header -------\n"
BD_TITLE = "\n-------- Body --------\n"


def parse_version(version):
    pattern = re.compile(
        r"^(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
        r"build((?P<build>\d+)),\d+\s+\((?P<release_type>.*?)\)"
    )
    matched = pattern.search(version)
    return matched.groupdict() if matched else {}


class TransformedDict(MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = {}
        self.update(dict(*args, **kwargs))

    def __value_transform__(self, value):
        return value

    def __getitem__(self, key):
        return self.__value_transform__(self.store[self.__keytransform__(key)])

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key


def extract_key(strfmt):
    return [fname for _, fname, *_ in Formatter().parse(strfmt) if fname]


def url_check(prefix, url, overlap_prefix="/api/v"):
    index = 0
    if url.startswith(overlap_prefix) and overlap_prefix in prefix:
        index = url.find("/", len(overlap_prefix))
    nurl = prefix.rstrip("/") + url[index:]
    return nurl


def wrap_as_title(sstr="", width=70, fill="-"):
    """print sstr with a fixed width (default is 70), fill with 'fill'
    return the printed string as well"""
    content = "{0}{1}{0}".format(fill, sstr)
    return (content if sstr else "").center(width, fill)


def http_request_to_string(request):
    """
    print request to list it's method, request url, header, body,
    and retrun it as a string the caller
    """
    headers = "\n".join("{}: {}".format(k, v) for k, v in request.headers.items())
    title = wrap_as_title("Request")
    status_line = request.method + " " + request.url
    body = "" if "cls/data" in request.url else format_to_string(request.body)
    request_string = "{1}{0}{1}{1}{2}{3}{4}{5}{6}{1}".format(
        title, "\n", status_line, HD_TITLE, headers, BD_TITLE, body
    )
    return request_string

    # Response had implemented this, can't use True or False to check Response
    # def __bool__(self):
    #     """Returns True if :attr:`status_code` is less than 400.

    #     This attribute checks if the status code of the response is between
    #     400 and 600 to see if there was a client error or a server error. If
    #     the status code, is between 200 and 400, this will return True. This
    #     is **not** a check to see if the response code is ``200 OK``.
    #     """
    #     return self.ok


def http_response_to_string(response):
    title = wrap_as_title("Response")
    headers = "\n".join(["{}: {}".format(k, v) for k, v in response.headers.items()])
    body = format_to_string(response)
    status_line = "{} {}".format(response.status_code, response.url)
    template = "{1}{0}{1}{1}{2}{3}{4}{5}{6}{1}"
    formatted = template.format(
        title, "\n", status_line, HD_TITLE, headers, BD_TITLE, body
    )
    return formatted


def pprint_http_request(res, func=logger.info):
    """
    update csrf toke451n after each request if there wasn't a access_token
    there write reqest and response to logging file, print request and
    response if verbosity is 2
    """
    request_in_string = http_request_to_string(res.request)
    func(request_in_string)
    response_in_string = http_response_to_string(res)
    func(response_in_string)


def format_to_string(original):
    if original is None:
        return ""
    if isinstance(original, requests.Response):
        return response_body_to_string(original)
    if isinstance(original, str):
        return format_string_to_json_string(original)
    if isinstance(original, dict):
        return json.dumps(original, sort_keys=True, indent=4)
    return original


def format_string_to_json_string(original):
    try:
        json_object = json.loads(original)
    except json.decoder.JSONDecodeError:
        formatted = original if len(original) <= 1024 else original[:1024] + "..."
    else:
        formatted = json.dumps(json_object, sort_keys=True, indent=4)
    return formatted


def response_body_to_string(response):
    try:
        json_body = response.json()
    except ValueError as e:
        logger.debug("Decode reponse error: %s", e)
        formatted = (
            response.text
            if len(response.text) <= 1024
            else response.text[:1024] + "..."
        )
    else:
        formatted = json.dumps(json_body, sort_keys=True, indent=4)
    return formatted
