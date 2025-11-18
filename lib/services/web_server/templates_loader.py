import os

from jinja2 import Environment, FileSystemLoader

# Template directory for web server templates
WEB_SERVER_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates"
)

# Jinja2 environment for web server templates
web_server_template_env = Environment(loader=FileSystemLoader(WEB_SERVER_TEMPLATE_DIR))
