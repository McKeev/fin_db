"""Logger configuration for fin_db."""
import logging
import colorlog
from pathlib import Path
from fin_db.helpers.telebot import get_telebot


_logging_configured = False


class TelegramCriticalHandler(logging.Handler):
    def __init__(self, lead: str = "🚨 FIN_DB CRITICAL ALERT"):
        super().__init__(level=logging.CRITICAL)
        self.lead = lead

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = f"{self.lead}\n\n{self.format(record)}"
            get_telebot().send_msg(text)
        except Exception:
            self.handleError(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: str | None = None,
    telegram_critical: bool = False,
) -> logging.Logger:
    """
    Configure root logging once for the whole process.

    Parameters
    ----------
    name : str
        Name for the logger instance to return. This is typically __name__ of
        the caller.
    level : int, default=logging.INFO
        Logging level
    log_file : str, optional
        Path to log file. If provided, logs will be written to this file.
        Parent directories will be created if they don't exist.
    telegram_critical : bool, default=False
        If True, critical log messages will be sent to the configured Telegram
        bot singleton.
    Returns
    -------
    logging.Logger
        Logger instance for the specified name.
    """
    global _logging_configured
    root = logging.getLogger()

    # Idempotent: don't add duplicate handlers if called again
    if _logging_configured:
        return logging.getLogger(name)

    root.setLevel(level)

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

    root.addHandler(console_handler)

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
        root.addHandler(file_handler)

    # Telegram critical handler if telegram_critical is True
    if telegram_critical:
        tele_handler = TelegramCriticalHandler()
        tele_handler.setLevel(logging.CRITICAL)
        tele_handler.setFormatter(logging.Formatter(
            "%(asctime)s\n%(name)s | %(levelname)s\n\n%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root.addHandler(tele_handler)

    _logging_configured = True

    return logging.getLogger(name)
