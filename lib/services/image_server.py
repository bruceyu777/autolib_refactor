import os
import socket
import time

import pandas as pd
import requests
import urllib3

from lib.utilities import (
    ImageNotFound,
    OperationFailure,
    UnSupportedModel,
    sleep_with_progress,
)

from .fos.fos_platform import platform_manager
from .log import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IMAGE_SERVER_FQDN = "releaseqa-imageserver.corp.fortinet.com"
IMAGE_STORE_DIR = r"/tftpboot/"

try:
    IMAGE_SERVER_IP = socket.gethostbyname(IMAGE_SERVER_FQDN)
except socket.error:
    logger.error("Unable to resolve Image Server FQDN: '%s'", IMAGE_SERVER_FQDN)
    IMAGE_SERVER_IP = "172.18.52.254"


class ImageServer:
    TFTP_PORT = 69
    MD5_FILE = "md5sum.txt"

    def __init__(self):
        self.url_prefix = f"https://{IMAGE_SERVER_FQDN}"

    def get_build_files(self, project, major, build):
        template = "{}/api/files?project={}&version={}&build={}"
        endpoint = template.format(self.url_prefix, project, major, build)
        logger.debug("GET %s", endpoint)
        try:
            response = requests.get(endpoint, timeout=30, verify=False)
            files = response.json()
            logger.debug("Files: %s", files)
        except Exception as e:
            logger.error("Query build file failure!(%s)", e)
            files = []
        if files:
            return files
        logger.error(
            "Request image is NOT ready yet for %s, v%s, build%s",
            project,
            major,
            build,
        )
        raise OperationFailure(response.text)

    def lookup_image(self, image):
        image_files = self.get_build_files(image.project, image.major, image.build)
        for image_file in image_files:
            if image.is_required(image_file["name"]):
                return image_file
        logger.info("failed to get an image!!!")
        return {}

    def get_image_http_url(self, image, use_ip=True):
        image_abs_path = self.locate_image(image)
        if not image_abs_path:
            raise ImageNotFound(image)
        _server = IMAGE_SERVER_IP if use_ip else IMAGE_SERVER_FQDN
        return f"https://{_server}/{image_abs_path}"

    def locate_image(self, image):
        image_info = self.lookup_image(image)
        if not image_info:
            raise ImageNotFound(image)
        abs_path = self.generate_image_abs_path(image_info)
        return abs_path

    @staticmethod
    def generate_image_abs_path(image):
        return (image["parent_dir"] + "/" + image["name"]) if image else ""

    def download_an_image(self, image, save_to_folder):
        image_url = self.get_image_http_url(image)
        start = time.time()
        image_location = self._retrieve_file(image_url, save_to_folder)
        logger.info("Done! consumed: %.2f(s)\n", float(time.time() - start))
        return image_location

    def _retrieve_file(self, image_path, save_to_folder):
        filename = os.path.basename(image_path)
        saved_file = os.path.join(save_to_folder, filename)
        sleep_interval = 30
        while sleep_interval <= sleep_interval * 2 * 2:
            logger.info("\nTry to download image:\n%s\n", image_path)
            try:
                if os.path.exists(saved_file):
                    os.remove(saved_file)
                with requests.get(
                    image_path, stream=True, verify=False, timeout=60 * 10
                ) as response:
                    response.raise_for_status()
                    with open(saved_file, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                logger.info("\n\nDownloaded to:\n%s\n", saved_file)
                return saved_file
            except Exception:  # pylint: disable = broad-except
                logger.error("Failed to download file from server: %s", image_path)
                sleep_interval *= 2
                sleep_with_progress(sleep_interval)
        raise OperationFailure("Failed to download file from server after 3 retries!!!")

    def get_builds(self, project, release, local=True):
        """[
                {
                    "build": "string",
                    "syncing": true,
                    "ga": true,
                    "release_tag": "string"
                }
        ]"""
        template = "{}/api/builds?project={}&version={}&local={}"
        endpoint = template.format(
            self.url_prefix, project, release, str(local).lower()
        )
        response = requests.get(endpoint, timeout=30, verify=False)
        return response.json()

    def get_major_branches(self, project):
        template = "{}/api/releasetags?project={}"
        endpoint = template.format(self.url_prefix, project)
        response = requests.get(endpoint, timeout=30, verify=False)
        tags = (tag["release_tag"] for tag in response.json())
        return [tag for tag in tags if all(s.isdigit() for s in tag.split("."))]

    def _get_all_build_of_major(self, project, branches, start_point=5):
        builds = []
        major = {m for m in branches if m > start_point}
        for m in major:
            builds += self.get_builds(project, m)
        return builds

    @staticmethod
    def _filter_builds(builds, branches):
        return [
            build
            for build in builds
            if any(build["release_tag"].startswith(b) for b in branches)
        ]

    def print_latest_builds(self, project, branches=None, count=3):
        branches = branches or self.get_major_branches(project)
        majors = {int(version.split(".")[0]) for version in branches}
        builds = self._get_all_build_of_major(project, majors)
        selected = self._filter_builds(builds, branches)
        dataframe = pd.DataFrame(selected)
        dataframe = (
            dataframe.sort_values(
                ["release_tag", "build"],
                ascending=False,
            )
            .groupby("release_tag")
            .head(count)
        )
        dataframe = dataframe.reset_index(drop=True)
        dataframe.columns = dataframe.columns.str.upper()

        for release, item in dataframe.groupby("RELEASE_TAG"):
            message = "\n" + " Release {} ".format(release).center(40, "+")
            logger.info(message)
            release_dataframe = item.reset_index(drop=True)
            release_dataframe.index += 1
            logger.info(release_dataframe)
        logger.info("\n")
        if not dataframe.empty:
            logger.info("***** !!Do NOT download SYNCING is True build!! *****")


class Image:
    def __init__(self, model, release, build, image_file_ext=".out"):
        self.model = model
        self.release = release
        self.build = "{0:04d}".format(int(build or 0))
        self.image_file_ext = image_file_ext

    @property
    def major(self):
        return self.release.split(".")[0]

    @property
    def project(self):
        if self.model.startswith(("FGT", "FFW")):
            return "FortiOS"
        raise UnSupportedModel(self.model)

    def __str__(self):
        return f"Model: {self.model}, Build: {self.build}, Release: {self.release}"

    def is_required(self, image_name):
        return image_name.startswith(self.model) and image_name.endswith(
            self.image_file_ext
        )


image_server = ImageServer()


def imageservice_operations(
    fortigates, project, release, build, image_type, query_only, home_directory="./"
):
    platforms = (platform_manager.normalize_platform(fgt) for fgt in fortigates)
    images = [Image(p, release, build, image_type) for p in platforms]

    if query_only:
        if not images:
            image_server.print_latest_builds(
                project, branches=[release] if release else []
            )
        else:
            for image in images:
                logger.info(
                    "%s: %s", image.model, image_server.get_image_http_url(image)
                )
    else:
        for image in images:
            image_server.download_an_image(image, home_directory)
    return ""


if __name__ == "__main__":
    t1 = time.perf_counter()
    image_server.download_an_image(Image("FGT_VM64_KVM", "7.4.1", "2493"), "./")
    t2 = time.perf_counter()
    print(f"Time taken: {t2 - t1}s")
