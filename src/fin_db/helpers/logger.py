"""Logger configuration for fin_db."""
import logging
import colorlog
from pathlib import Path


def setup_logger(
    name: str, level: int = logging.INFO, log_file: str | None = None
) -> logging.Logger:
    """
    Set up a colored logger with optional file output.

    Parameters
    ----------
    name : str
        Logger name
    level : int, default=logging.INFO
        Logging level
    log_file : str, optional
        Path to log file. If provided, logs will be written to this file.
        Parent directories will be created if they don't exist.

    Returns
    -------
    logging.Logger
        Configured logger instance with console and optional file handlers
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s "
            "%(blue)s%(name)s%(reset)s: %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )

    logger.addHandler(console_handler)

    # File handler if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)-8s - %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger
