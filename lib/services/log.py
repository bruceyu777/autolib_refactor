import logging
import sys
from pathlib import Path

from .output import output

logger = logging.getLogger()


def add_logging_level(levelName, levelNum, methodName=None):
    methodName = levelName.lower()

    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(  # pylint: disable= protected-access
                levelNum, message, args, **kwargs
            )

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


def add_logger_handler(handler, level, formatter):
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def add_stdout_stream():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(message)s")
    add_logger_handler(handler, logging.NOTICE, formatter)  # pylint: disable= no-member


def add_file_stream(in_debug_mode):
    if in_debug_mode:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        formatter = logging.Formatter("%(message)s")
    log_file = output.compose_summary_file("autotest.log")
    handler = logging.FileHandler(log_file)
    level = logging.DEBUG if in_debug_mode else logging.INFO
    add_logger_handler(handler, level, formatter)
    return handler


def update_output_subfolder(is_group_test, env_config_filename):
    test_type = "group" if is_group_test else "script"
    folder_suffix = f"{test_type}--{Path(env_config_filename).stem}"
    output.update_output_folder_suffix(folder_suffix)


def setup_logger(in_debug_mode, is_group_test, env_config_filename, sub_command=False):
    log_level = logging.DEBUG if in_debug_mode else logging.INFO
    if sub_command:
        enable_log_for_subcommand(log_level)
    else:
        enable_log_for_autotest(log_level, is_group_test, env_config_filename)


def enable_log_for_autotest(log_level, is_group_test, env_config_filename):
    update_output_subfolder(is_group_test, env_config_filename)
    add_logging_level("NOTICE", logging.INFO + 10)
    logger.setLevel(log_level)
    setattr(logger, "in_debug_mode", log_level is logging.DEBUG)
    add_stdout_stream()
    job_log_handler = add_file_stream(log_level is logging.DEBUG)
    setattr(logger, "job_log_handler", job_log_handler)


def enable_log_for_subcommand(level):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.setLevel(level)
    logger.addHandler(handler)
