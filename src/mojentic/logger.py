import logging

logger = logging.getLogger("mojentic")
logging.basicConfig(filename='output.log', level=logging.DEBUG)
logger.info("Starting logger")
