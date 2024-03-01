import logging

from lib.services.log import logger, set_logger


def test_set_logger():
    set_logger()
    level = logger.getEffectiveLevel()
    assert level == logging.DEBUG
