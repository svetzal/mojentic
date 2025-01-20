import logging
from pathlib import Path

logger = logging.getLogger("mojentic")
path = Path().cwd()
log_filename = path / 'output.log'
print(f"Logging to {log_filename}")
logging.basicConfig(filename=log_filename, level=logging.DEBUG)
logger.info("Starting logger")
