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


def add_stdout_stream(run_mode):
    handler = logging.StreamHandler(sys.stdout)
    if run_mode == "debug":
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        add_logger_handler(handler, logging.DEBUG, formatter)
        return
    formatter = logging.Formatter("%(message)s")

    add_logger_handler(
        handler, logging.ERROR, formatter  # pylint: disable= no-member
    )
    add_logger_handler(
        handler, logging.NOTICE, formatter  # pylint: disable= no-member
    )


def add_file_stream():
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = output.compose_summary_file("autotest.log")
    handler = logging.FileHandler(log_file)
    add_logger_handler(handler, logging.DEBUG, formatter)


def set_logger(run_mode):
    logger.setLevel(logging.DEBUG)
    add_logging_level("NOTIFY", logging.INFO + 5)
    add_logging_level("NOTICE", logging.INFO + 10)
    add_stdout_stream(run_mode)
    add_file_stream()
