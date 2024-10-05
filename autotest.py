#!/usr/bin/python3

import argparse
import os
import sys

from lib.core.scheduler.job import Job
from lib.services import logger, set_logger
from lib.services.summary import summary


class Upgrade(argparse.Action):
    def __init__(self, option_strings, dest, nargs=0, **kwargs):
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)
        self.binary_filename = kwargs.get("binary_filename", "AutoLib_v3")
        self.release_on_server = kwargs.get(
            "release_on_server", f"http://172.18.52.254/AutoLib/{self.binary_filename}"
        )

    def __call__(self, parser, namespace, values, option_string=None):
        self._upgrade()

    def _upgrade(self):
        # Create a pipe for communication between parent and child processes
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid > 0:
            self._parent_process(read_fd, write_fd)
        else:
            self._child_process(write_fd)

    def _parent_process(self, read_fd, write_fd):
        os.close(write_fd)
        with os.fdopen(read_fd) as read_pipe:
            while True:
                line = read_pipe.readline()
                if not line:
                    break
                print(line, end="")
                sys.stdout.flush()
        sys.exit(0)

    def _child_process(self, write_fd):
        self._close_unused_fds(write_fd)
        with os.fdopen(write_fd, "w") as write_pipe:
            write_pipe.write("Started to upgrade.\n")
            if self._upgrade_logic():
                write_pipe.write("Succeeded to upgrade.\n")
            else:
                write_pipe.write("Failed to upgrade.\n")
        sys.exit(0)

    def _close_unused_fds(self, write_fd):
        max_fd = os.sysconf("SC_OPEN_MAX") if hasattr(os, "sysconf") else 2048
        for fd in range(3, max_fd):
            if fd == write_fd:
                continue
            try:
                os.close(fd)
            except OSError:
                pass

    def _upgrade_logic(self):
        os.system(f"rm -rf {self.binary_filename}")
        exit_status = os.system(f"curl -O {self.release_on_server}")
        return exit_status == 0


PROG_DESCRIPTION = """Regression Test Automation Framework.
Document link: https://releaseqa-portal.corp.fortinet.com/static/docs/training/autolib_v3_docs/"""

SUBMIT_HELP = """all: submit all testcases' result to Oriole.
none: do not submit any testcase result to Oriole.
succeeded: only submit succeeded testcases' result to Oriole."""


__version__ = "V3R10B0003"


def parse_cli_args():
    parser = argparse.ArgumentParser(
        prog="AutoLib_v3",
        description=PROG_DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "-u",
        "--upgrade",
        action=Upgrade,
        help="Upgrade current AutoLib",
    )
    parser.add_argument(
        "-e",
        "--environment",
        dest="env",
        help="Environment file",
        required=False,
    )
    parser.add_argument(
        "-t", "--testcase", dest="script", help="Testcase file", required=False
    )
    parser.add_argument(
        "-g", "--group", dest="group", help="Testgroup file", required=False
    )
    parser.add_argument(
        "-r",
        "--release",
        dest="release",
        help="Release major version",
        required=False,
    )
    parser.add_argument(
        "-b", "--build", dest="build", help="Build number", required=False
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="enanble debug",
        required=False,
    )
    parser.add_argument(
        "-c",
        "--check",
        dest="check",
        action="store_true",
        default=False,
        help="only do syntax check",
        required=False,
    )
    parser.add_argument(
        "-re",
        "--reset",
        dest="reset",
        action="store_true",
        default=False,
        help="if factory reset is needed for upgrading",
        required=False,
    )
    parser.add_argument(
        "-bn",
        "--burn",
        dest="burn",
        action="store_true",
        default=False,
        help="if image burning is needed for upgrading",
        required=False,
    )
    parser.add_argument(
        "-s",
        "--submit",
        dest="submit_flag",
        choices=["all", "none", "succeeded"],
        default="succeeded",
        help=SUBMIT_HELP,
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_cli_args()
    set_logger(args.debug)

    if not (args.script or args.group):
        logger.error("Please speicify the testcase script or testcase group.")
        sys.exit(-1)

    logger.notice("Start test job.")
    if args.script:
        logger.notice("Test script is %s", args.script)
        test_file = args.script
    else:
        logger.notice("Test group is %s", args.group)
        test_file = args.group
    logger.notice("Test environment file is %s", args.env)

    summary.dump_str_to_brief_summary(
        f"Environment File: {args.env}, Test File: {test_file}"
    )

    try:
        Job(args).run()
        logger.notice("Test job finised.")
    except Exception:
        logger.exception("Test job failed.")
        if not args.check:
            sys.exit(-1)
    sys.exit(0)


if __name__ == "__main__":
    main()
