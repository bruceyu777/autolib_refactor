#!/usr/bin/python3

import argparse
import os
import sys

from lib import (
    PARAGRAPH_SEP,
    ApiRegistry,
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

# pylint: disable=protected-access
if hasattr(sys, "_MEIPASS"):
    # Get the path to the temporary directory where PyInstaller extracts files
    # This attribute is only available when the application is running
    # from a PyInstaller bundle.
    version_file_path = os.path.join(sys._MEIPASS, "version")
else:
    # If running from source code, use the current working directory
    version_file_path = "./version"

try:
    with open(version_file_path, "r", encoding="utf-8") as f:
        __version__ = f.read().strip()
except FileNotFoundError:
    print("Error: version file not found.")
    __version__ = "unknown"


def create_webserver_parser(parent):
    parser = parent.add_parser(
        "webserver",
        help="Launch Autotest HTTP Web Server",
        description="To launch Autotest HTTP Web Server as Working Portal",
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


def create_upgrade_parser(parent):
    """Create the parser for the upgrade subcommand"""
    upgrade_parser = parent.add_parser(
        "upgrade",
        help="Upgrade current autotest binary",
        description="Upgrade current autotest binary",
    )
    upgrade_parser.add_argument(
        "-b",
        "--build",
        dest="build",
        help="Specific build number, by default upgrade to the latest version if branch is not specified",
    )
    upgrade_parser.add_argument(
        "--branch",
        dest="branch",
        default="V3R10",
        help="Specify the branch to upgrade, default is V3R10",
    )
    return upgrade_parser


def create_api_docs_parser(parent):
    """Create the parser for the api_docs subcommand"""
    api_docs_parser = parent.add_parser(
        "api_docs",
        help="Query available API documentation",
        description="Query help information for API",
    )
    api_docs_parser.add_argument(
        "-a",
        "--api",
        dest="api_endpoint",
        help="Specific API name to query (shows all if not specified)",
    )
    api_docs_parser.add_argument(
        "-c",
        "--category",
        dest="category",
        help="Filter APIs by category",
    )
    api_docs_parser.add_argument(
        "-l",
        "--list-categories",
        dest="list_categories",
        action="store_true",
        default=False,
        help="List all available categories",
    )
    return api_docs_parser


def create_main_parser():
    parser = argparse.ArgumentParser(
        prog="autotest",
        description=PROG_DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
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
        help="enable debug",
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
        help="Specify a timeout timer for waiting image ready.(Unit: Hour)",
    )
    parser.add_argument(
        "--portal",
        dest="portal",
        action="store_true",
        default=False,
        help="Bring up web portal while run autotest",
    )
    parser.add_argument(
        "--non_strict",
        dest="non_strict",
        action="store_true",
        default=False,
        help="Disable strict mode to allow the script to run even if it contains syntax errors",
    )
    parser.add_argument(
        "--task_path",
        dest="task_path",
        help="Specify Oriole task path to send test results.",
    )
    return parser


def parse_cli_args():
    parser = create_main_parser()
    subparsers = parser.add_subparsers(dest="command", help="Sub commands")
    create_upgrade_parser(subparsers)
    create_webserver_parser(subparsers)
    create_imageservice_parser(subparsers)
    create_api_docs_parser(subparsers)
    args = parser.parse_args()
    return args


def run_autotest_main(args):
    if not (args.script or args.group):
        logger.error("Please specify the testcase script or testcase group.")
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


def run_api_docs(args):
    """Handle the api_docs subcommand"""

    registry = ApiRegistry()

    # List categories
    if args.list_categories:
        categories = registry.list_categories()
        print(f"Available API Categories:\n{PARAGRAPH_SEP}")
        for cat in categories:
            ops_count = len(registry.list_apis(cat))
            print(f"  • {cat:40s} ({ops_count} APIs)")
        print(f"{PARAGRAPH_SEP}\n\nTotal: {len(categories)} categories")
        return

    # Show specific operation info
    if args.api_endpoint:
        if not registry.has_api(args.api_endpoint):
            print(f"Error: API '{args.api_endpoint}' not found.")
            print("\nUse 'autotest api_docs' to list all APIs.")
            sys.exit(1)

        info = registry.get_api_info(args.api_endpoint)
        print(f"{PARAGRAPH_SEP}\nAPI: {info['name']}\n{PARAGRAPH_SEP}")
        print(f"{info['full_doc']}\n{PARAGRAPH_SEP}")
        return

    # Filter by category
    if args.category:
        apis = registry.list_apis(args.category)
        if not apis:
            print("\nUse 'autotest api_docs --list-categories' to see all categories.")
            sys.exit(1)

        print(f"{PARAGRAPH_SEP}\nAPIs in '{args.category}' Category\n{PARAGRAPH_SEP}\n")
        for api_endpoint in apis:
            info = registry.get_api_info(api_endpoint)
            print(f"\n{api_endpoint}")
            print("-" * len(api_endpoint))
            print(info["description"])
        print(f"\n{PARAGRAPH_SEP}\nTotal: {len(apis)} apis in '{args.category}'")
        return

    # Show all apis grouped by category
    registry.print_all_apis()


def run_sub_command_main(args):
    if args.command == "upgrade":
        Upgrade(args.build, branch=args.branch).run()
    elif args.command == "webserver":
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
    elif args.command == "api_docs":
        run_api_docs(args)


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
