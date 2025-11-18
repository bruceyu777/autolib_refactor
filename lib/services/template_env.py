import os

from jinja2 import Environment, FileSystemLoader

TEMPLATE_FILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
web_server_env = Environment(loader=FileSystemLoader(TEMPLATE_FILE_DIR))

TEMPLATE_FILENAME = "summary.template"
LOADED_SUMMARY_TEMPLATE = web_server_env.get_template(TEMPLATE_FILENAME)

__all__ = ["LOADED_SUMMARY_TEMPLATE"]
