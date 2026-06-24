import logging
from pythonjsonlogger import jsonlogger
import sys

def get_logger(name: str):
    logger = logging.getLogger(name)
    
    # Only configure if it hasn't been configured yet to avoid duplicate logs
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        
        # This formats the log as a JSON object with timestamp, level, name, and message
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger