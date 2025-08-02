import logging, sys

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:            # already configured
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('%(asctime)s — %(levelname)s — %(name)s — %(message)s')
    )
    logger.addHandler(handler)
    return logger

get_logger = setup_logger         # alias
