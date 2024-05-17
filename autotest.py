#!/usr/bin/python3

import argparse
import sys
import os

from lib.core.scheduler.job import Job
from lib.services import logger, set_logger
from lib.utilities.exceptions import CompileException, FileNotExist


class Upgrade(argparse.Action):
    def __init__(self, option_strings, dest, nargs=0, **kwargs):
        super(Upgrade, self).__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        exit_status = os.system("curl -O http://172.18.52.254/AutoLib/AutoLib_v3")
        if exit_status == 0:
            print("Succeeded to upgrade.")
        else:
            print("Failed to upgrade.")
        sys.exit(0)


PROG_DESCRIPTION = """Regression Test Automation Framework.
Document link: https://releaseqa-portal.corp.fortinet.com/static/docs/training/autolib_v3_beta/"""

SUBMIT_HELP = """all: submit all testcases' result to oriole.
none: do not submit any testcase result to oriole.
succeeded: only submit succeeded testcases' result to oriole."""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="AutoLib_v3",
        description=PROG_DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("-v", '--version', action="version",
                    version="AutoLib 3.0.5")
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
        "-s",
        "--submit",
        dest="submit_flag",
        choices=["all", "none", "succeeded"],
        default="succeeded",
        help=SUBMIT_HELP
    )
    args = parser.parse_args()
    run_mode = "debug" if args.debug else "run"
    set_logger(run_mode)

    if not args.script and not args.group:
        logger.error("Please speicify the testcase script or testcase group.")

    logger.notice("Start test job.")
    if args.script:
        logger.notice("Test script is %s", args.script)
    if args.group:
        logger.notice("Test group is %s", args.group)
    logger.notice("Test environment file is %s", args.env)

    try:
        job = Job(args)
        job.run()
    except Exception as e:
        logger.error(e.message)
        if not args.check:
            sys.exit(-1)

    logger.notice("Test job finised.")
    sys.exit(0)
