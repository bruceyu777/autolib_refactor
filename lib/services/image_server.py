import os
import sys
import time

import requests
import tftpy

from lib.utilities.exceptions import ImageNotFound, OperationFailure, UnSupportedModel

from .log import logger

DEPLOYMENT = "deploy"
UPGRADE = "upgrade"
TFTP_SERVER_IP = "172.18.52.254"
IMAGE_STORE_DIR = r"/qaserver/tftpboot/"


class DownloadProgress:
    """download progress bar"""

    def __init__(self, file_size):
        self.filesize = file_size
        self.so_far = 0
        self.count = 0

    def ddcallback(self, tftp_packet):
        self.count += 1
        if not hasattr(tftp_packet, "data"):
            return
        self.so_far = self.so_far + len(tftp_packet.data)
        if self.count % 150 == 0 or self.so_far == self.filesize:
            progress = self.so_far / self.filesize
            self.update_progress(progress)
        return

    @staticmethod
    def update_progress(progress):
        length = 38
        block = int(round(length * progress))
        msg = "\r{0:}: [{1}] {2: 3}%".format(
            "Approaching",
            "#" * block + "-" * (length - block),
            round(progress * 100, 1),
        )
        sys.stdout.write(msg)
        sys.stdout.flush()


class ImageServer:
    TFTP_PORT = 69
    MD5_FILE = "md5sum.txt"
    IMAGE_MICROSERVICE_PORT = 8090

    def __init__(self, work_dir=IMAGE_STORE_DIR):
        self.work_dir = work_dir
        self.url_prefix = "http://{}:{}".format(
            TFTP_SERVER_IP,
            self.IMAGE_MICROSERVICE_PORT,
        )

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
        image_info = self.lookup_image(image)
        abs_path = self.generate_image_abs_path(image_info)

        start = time.time()
        image_location = self._retrieve_file(abs_path, image_info["size"])
        logger.info("Done! consumed: %d(s)\n", int(time.time() - start))
        return image_location

    def _retrieve_file(self, image_path, total_size):
        filename = os.path.basename(image_path)
        saved_file = self.work_dir + filename
        count, sleep_interval = 0, 10
        tftp_client = tftpy.TftpClient(
            TFTP_SERVER_IP,
            self.TFTP_PORT,
            options={"blksize": 14680},
        )
        progress_bar = DownloadProgress(total_size)
        while count < 3:
            logger.info("\nTry to download image:\n%s\n", image_path)
            try:
                tftp_client.download(
                    image_path,
                    saved_file,
                    packethook=progress_bar.ddcallback,
                    timeout=60,
                )
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
        # breakpoint()
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
    import time

    t1 = time.perf_counter()
    image_server.download_an_image(Image("FGT_VM64_KVM", "7.4.1", "2493"))
    t2 = time.perf_counter()
    print(f"Time taken: {t2 - t1}s")
