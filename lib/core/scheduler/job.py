import os
import webbrowser
import time


from lib.services import env, oriole, output, logger
from lib.core.scheduler.web_server import WebServer
from .group_task import GroupTask
from .script_task import ScriptTask


import pdb

class Job:
    def __init__(self, args):
        self.args = args

    def execute_script(self):
        if self.args.script:
            task = ScriptTask(self.args.script)
        if self.args.group:
            task = GroupTask(self.args.group)
        task.run(self.args)

    def start_http_server(self):
        ip, port = env.get_local_http_server_conf()
        if ip and port:
            WebServer(ip, port).start()
        else:
            exit(0)

    def init_env(self):
        env.init_env(self.args)
        oriole.set_user_cfg(self.args)

    def create_child_process(self):
        pid = os.fork()
        if pid == 0:
            self.start_http_server()
        else:
            logger.info('After creating web server for autotest.')
            ip, port = env.get_local_http_server_conf()
            if ip and port:
                logger.notice(f"Summary: http://{ip}:{port}/{output.get_current_output_dir()}/summary/summary.html")
                webbrowser.open_new(f"http://{ip}:{port}/{output.get_current_output_dir()}/summary/")

            self.execute_script()
            if self.args.submit_flag != "none":
                oriole.submit()

    def run(self):
        self.init_env()
        self.create_child_process()


