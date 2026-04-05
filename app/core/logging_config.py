from loguru import logger
import sys


def setup_logging(log_level: str = "INFO", log_file: str = "/var/log/fastapi/app.log"):
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    logger.add(
        log_file,
        level=log_level,
        rotation="500 MB",
        retention="7 days"
    )
    return logger
