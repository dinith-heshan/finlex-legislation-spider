import logging

def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    file = logging.FileHandler("tests/logging-module-test/app.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    console.setFormatter(fmt)
    file.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file)

    return logger

logger = setup_logger()

logger.info("App started")