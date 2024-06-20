#!/usr/bin/python3

import argparse
import sys
import time
import os
import requests
# import pdb
from lib.core.scheduler.job import Job
from lib.services import logger, set_logger
from lib.utilities.exceptions import CompileException, FileNotExist

from lib.services.summary import summary
from lib.services.output import output

class Upgrade(argparse.Action):
    def __init__(self, option_strings, dest, nargs=0, **kwargs):
        super(Upgrade, self).__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        r, w = os.pipe()
        pid = os.fork()
        if pid > 0:
            os.close(w)
            r = os.fdopen(r)
            str = ""
            while "Succeeded" not in str and "Failed" not in str:
                str = r.read()
                print(str)
                sys.stdout.flush()

            sys.exit(0)
        else:
            os.umask(0)

            # Close all open file descriptors except for stdin, stdout, and stderr
            max_fd = os.sysconf("SC_OPEN_MAX") if hasattr(os, "sysconf") else 2048
            for fd in range(3,max_fd):
                try:
                    if w == fd:
                        continue
                    os.close(fd)
                except OSError:
                    pass
            w = os.fdopen(w, 'w')
            w.write("Started to upgrade.\n")
            os.system("rm -rf AutoLib_v3")
            exit_status = os.system("curl -O http://172.18.52.254/AutoLib/AutoLib_v3")
            if exit_status == 0:
                w.write("Succeeded to upgrade.\n")
            else:
                w.write("Failed to upgrade.\n")

            w.close()
            sys.exit(0)

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
                    version="AutoLib 3.0.9")
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
        help="if need factory reset for upgrading",
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
    test_file = None
    if args.script:
        logger.notice("Test script is %s", args.script)
        test_file = args.script
    if args.group:
        logger.notice("Test group is %s", args.group)
        test_file = args.group
    logger.notice("Test environment file is %s", args.env)

    summary.dump_str_to_brief_summary(f"Environment File: {args.env}, Test File: {test_file}")

    try:
        job = Job(args)
        job.run()
        logger.notice("Test job finised.")
    except Exception as e:
        logger.error(e.message)
        if not args.check:
            sys.exit(-1)
    # finally:
        # output.zip_autotest_log()
    sys.exit(0)
