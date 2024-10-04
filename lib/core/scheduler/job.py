import os
import sys
import webbrowser

from lib.core.scheduler.web_server import WebServer
from lib.services import env, logger, oriole, output

from .group_task import GroupTask
from .script_task import ScriptTask


class Job:
    def __init__(self, args):
        self.args = args

    def init_task(self):
        return (
            ScriptTask(self.args.script)
            if self.args.script
            else GroupTask(self.args.group)
        )

    def execute_script(self):
        task = self.init_task()
        task.run(self.args)
        output.zip_autotest_log()

    def start_http_server(self):
        ip, port = env.get_local_http_server_conf()
        if ip and port:
            WebServer(ip, port).start()
        else:
            sys.exit(0)

    def init_env(self):
        env.init_env(self.args)
        oriole.set_user_cfg(self.args)

    def _launch_summary_webpage(self):
        host, port = env.get_local_http_server_conf()
        if not host or not port:
            logger.error("Unable to get IP and PORT for LOCAL_HTTP_SERVER from env.")
            return

        summary_url = f"http://{host}:{port}/{output.get_current_output_dir()}/summary"
        logger.notice(f"Summary: {summary_url}/summary.html")
        webbrowser.open_new(summary_url)

    def create_child_process(self):
        pid = os.fork()
        if pid == 0:
            self.start_http_server()
        else:
            self._launch_summary_webpage()
            self.execute_script()

    def run(self):
        self.init_env()
        self.create_child_process()
