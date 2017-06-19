import logging
import sys

from pytest import fixture

from inxs import logger


stdout_handler = logging.StreamHandler(sys.stdout)


@fixture()
def info_logging():
    stdout_handler.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    logger.setLevel(logging.INFO)
    yield
    logger.removeHandler(stdout_handler)
