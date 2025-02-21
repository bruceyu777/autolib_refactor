#!/usr/bin/python3

import argparse
import sys

from lib import (
    Job,
    Upgrade,
    imageservice_operations,
    launch_webserver_on,
    logger,
    setup_logger,
)

PROG_DESCRIPTION = """Regression Test Automation Framework.
Document link: https://releaseqa-portal.corp.fortinet.com/static/docs/training/autolib_v3_docs/"""

SUBMIT_HELP = """all: submit all testcases' result to Oriole.
none: do not submit any testcase result to Oriole.
succeeded: only submit succeeded testcases' result to Oriole."""


__version__ = "V3R10B0005"


def create_webserver_parser(parent):
    parser = parent.add_parser(
        "webserver",
        help="Launch AutoLib HTTP Web Server",
        description="To launch AutoLib HTTP Web Server as Working Portal",
    )
    parser.add_argument(
        "-p", "--port", dest="port", help="Specify port number to listen", default=8080
    )
    parser.add_argument(
        "-i",
        "--ip_address",
        dest="ip_address",
        help="Specify ip address to listen",
        default="127.0.0.1",
    )


def create_imageservice_parser(parent):
    parser = parent.add_parser(
        "imageservice",
        help="Download or check image information",
        description="Use this command to check the latest image information or to download image:",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.1")
    parser.add_argument(
        "-b", "--build", dest="build", help="Specify the build number of the image"
    )
    parser.add_argument(
        "-x",
        "--ext",
        dest="ext",
        type=str,
        default=".out",
        help="Specify the image file extension",
    )
    parser.add_argument(
        "-r",
        "--release",
        dest="release",
        type=str,
        default="",
        help="Specify the major release",
    )
    parser.add_argument(
        "-p",
        "--project",
        dest="project",
        type=str,
        default="FortiOS",
        help="Specify the product project",
    )
    parser.add_argument(
        "-d",
        "--home_dir",
        dest="home_directory",
        type=str,
        default="/tftpboot/",
        help="Specify where to save downloaded image file",
    )
    parser.add_argument(
        "-f",
        "--fgt",
        dest="fortigates",
        nargs="*",
        default=[],
        help=(
            "1> FortiGate list from env.conf if you upgrade\n"
            "2> or platform if checking image file path\n"
            "3> if you have multiple one, use space to separate\n"
        ),
    )
    parser.add_argument(
        "-q",
        "--query",
        dest="only_query",
        action="store_true",
        default=False,
        help="Retrieve image information from the TFTP Server",
    )
    return parser


def create_main_parser():
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
    parser.add_argument(
        "-p",
        "--project",
        dest="project",
        default="FortiOS",
        help="Specify project for image downloading and checking...",
    )
    parser.add_argument(
        "-w",
        "--wait_image_ready_timer",
        type=int,
        default=0,
        dest="wait_image_ready_timer",
        help="Specify a tiemout timer for waiting image ready.(Unit: Hour)",
    )
    parser.add_argument(
        "--portal",
        dest="portal",
        action="store_true",
        default=False,
        help="Bring up web portal while run autotest",
    )
    return parser


def parse_cli_args():
    parser = create_main_parser()
    subprasers = parser.add_subparsers(dest="command", help="Sub commands")
    create_webserver_parser(subprasers)
    create_imageservice_parser(subprasers)
    args = parser.parse_args()
    return args


def run_autotest_main(args):
    if not (args.script or args.group):
        logger.error("Please speicify the testcase script or testcase group.")
        sys.exit(-1)

    logger.notice("\n**** Start test job with AUTOLIB - %s. ****", __version__)
    logger.notice("CLI from user: %s", " ".join(sys.argv))
    logger.notice("Test Environment: %s", args.env)

    try:
        Job(args).run()
        logger.notice("Test job is launched.")
    except Exception:
        logger.exception("Test job failed.")
        if not args.check:
            sys.exit(-1)


def run_sub_command_main(args):
    if args.command == "webserver":
        launch_webserver_on(args.ip_address, args.port)
    elif args.command == "imageservice":
        imageservice_operations(
            args.fortigates,
            args.project,
            args.release,
            args.build,
            args.ext,
            args.only_query,
            home_directory=args.home_directory,
        )


def main():
    args = parse_cli_args()
    setup_logger(
        args.debug, args.group, args.script or args.group, sub_command=args.command
    )
    if args.command:
        run_sub_command_main(args)
    else:
        run_autotest_main(args)


if __name__ == "__main__":
    main()
