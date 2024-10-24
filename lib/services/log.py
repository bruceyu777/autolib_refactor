import logging
import sys

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


def set_logger(in_debug_mode):
    add_logging_level("NOTICE", logging.INFO + 10)
    log_level = logging.DEBUG if in_debug_mode else logging.INFO
    logger.setLevel(log_level)
    setattr(logger, "in_debug_mode", in_debug_mode)
    add_stdout_stream()
    add_file_stream(in_debug_mode)
