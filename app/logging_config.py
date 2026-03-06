import logging
import platform
import sys


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info(
        "Starting converter with Python %s on %s",
        sys.version.split()[0],
        platform.system(),
    )
