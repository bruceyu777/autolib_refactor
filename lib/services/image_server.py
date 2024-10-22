import os
import socket
import sys
import time

import requests
import wget

from lib.utilities.exceptions import ImageNotFound, OperationFailure, UnSupportedModel

from .log import logger

DEPLOYMENT = "deploy"
UPGRADE = "upgrade"
IMAGE_SERVER_FQDN = "releaseqa-imageserver.corp.fortinet.com"
IMAGE_STORE_DIR = r"/qaserver/tftpboot/"

try:
    IMAGE_SERVER_IP = socket.gethostbyname(IMAGE_SERVER_FQDN)
except socket.error:
    logger.error("Unable to resolve Image Server FQDN: '%s'", IMAGE_SERVER_FQDN)
    IMAGE_SERVER_IP = "172.18.52.254"


class ImageServer:
    TFTP_PORT = 69
    MD5_FILE = "md5sum.txt"

    def __init__(self, work_dir=IMAGE_STORE_DIR):
        self.work_dir = work_dir
        self.url_prefix = f"https://{IMAGE_SERVER_FQDN}"

    def get_build_files(self, project, major, build):
        template = "{}/api/files?project={}&version={}&build={}"
        endpoint = template.format(self.url_prefix, project, major, build)
        response = requests.get(endpoint, timeout=30)
        if response.ok:
            return response.json()

        logger.error(
            "Failed to get image files for project: %s, version:%s, build: %s",
            project,
            major,
            build,
        )
        sys.exit(-1)
        # raise OperationFailure(response.text)

    def lookup_image(self, image):
        image_files = self.get_build_files(image.project, image.major, image.build)
        for image_file in image_files:
            if image.is_required(image_file["name"]):
                return image_file
        logger.info("failed to get an image!!!")
        return {}

    def get_image_http_url(self, image):
        image_abs_path = self.locate_image(image)
        if not image_abs_path:
            raise ImageNotFound(image)
        return f"https://{IMAGE_SERVER_FQDN}/{image_abs_path}"

    def locate_image(self, image):
        image_info = self.lookup_image(image)
        if not image_info:
            raise ImageNotFound(image)
        abs_path = self.generate_image_abs_path(image_info)
        return abs_path

    @staticmethod
    def generate_image_abs_path(image):
        return (image["parent_dir"] + "/" + image["name"]) if image else ""

    def download_an_image(self, image):
        image_url = self.get_image_http_url(image)
        start = time.time()
        image_location = self._retrieve_file(image_url)
        logger.info("Done! consumed: %d(s)\n", int(time.time() - start))
        return image_location

    def _retrieve_file(self, image_path):
        filename = os.path.basename(image_path)
        saved_file = self.work_dir + filename
        count, sleep_interval = 0, 10
        while count < 3:
            logger.info("\nTry to download image:\n%s\n", image_path)
            try:
                if os.path.exists(saved_file):
                    os.remove(saved_file)
                wget.download(image_path, saved_file)
                logger.info("\n\nDownloaded to:\n%s\n", saved_file)
                return saved_file
            except Exception:  # pylint: disable = broad-except
                time.sleep(10)
                logger.error("Failed to download file from server: %s", image_path)
                count += 1
                logger.info("Going to sleep %d...", sleep_interval)
                time.sleep(sleep_interval)
                sleep_interval *= 2
        raise OperationFailure("Failed to download file from server after 3 retries!!!")


class Image:
    def __init__(self, model, release, build, image_type=DEPLOYMENT):
        self.model = model
        self.release = release
        self.build = "{0:04d}".format(int(build or 0))
        self.image_type = image_type

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

    @property
    def _ext(self):
        extension = ".out"
        if "VM64" in self.model and self.image_type == DEPLOYMENT:
            extension += ".kvm.zip"
        return extension

    def is_required(self, image_name):
        return image_name.startswith(self.model) and image_name.endswith(self._ext)


image_server = ImageServer()


if __name__ == "__main__":
    t1 = time.perf_counter()
    image_server.download_an_image(Image("FGT_VM64_KVM", "7.4.1", "2493"))
    t2 = time.perf_counter()
    print(f"Time taken: {t2 - t1}s")
