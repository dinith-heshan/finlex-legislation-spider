import logging

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

console = logging.StreamHandler()
file = logging.FileHandler("tests/logging-module-test/app.log")

fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

console.setFormatter(fmt)
file.setFormatter(fmt)

logger.addHandler(console)
logger.addHandler(file)

logger.debug("log debug")
logger.info("log info")
logger.warning("log warning")
logger.error("log error")
logger.critical("log critical")