#!/usr/bin/python3

import argparse
import sys

from lib.core.scheduler.job import Job
from lib.services import logger, set_logger
from lib.utilities.exceptions import CompileException, FileNotExist

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="AutoLib_v3",
        description=("Regression Test Automation Framework.")
    )

    parser.add_argument("-v", '--version', action="version",
                    version="AutoLib 3.0.4")

    parser.add_argument(
        "-e",
        "--environment",
        dest="env",
        help="Environment file",
        required=True,
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
        help=(
            "all: submit all testcases' result to oriole. \n"
            "none: do not submit any testcase result to oriole. \n"
            "succeeded: only submit succeeded testcases' result to oriole"
        ),
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
