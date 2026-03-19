"""
File Name: telebot.py
Author: Cedric McKeever
Date: 2026-03-17
Description:
Allows sending messages to a Telegram bot for notifications (e.g. on script
completion or errors). Uses a singleton pattern to ensure only one bot instance
is created and used throughout the application.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
import logging
# Third Party Imports
import requests
# Local Imports


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------


class TeleBot:
    """
    Send messages with a Telegram bot for easy notifications.
    """

    def __init__(self, token: str, chat_id: str, timeout: int = 10) -> None:
        self.token = token
        self.chat_id = chat_id
        self.timeout = timeout

    def send_msg(self, message: str) -> bool:
        """
        Send a simple message to the Telegram bot.

        Parameters:
        ----------
        message: str
            The message to send.
        Returns:
        -------
        bool
            True if the message was sent successfully, False otherwise.
        """

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            ok = bool(data.get("ok", False))
            if not ok:
                logger.error(f"Telegram API returned non-ok response: {data}")
            return ok
        except requests.RequestException as e:
            logger.error(f"Failed to send message to Telegram bot: {e}")
            return False
        except ValueError as e:
            logger.error(f"Invalid Telegram API JSON response: {e}")
            return False


_bot: TeleBot | None = None


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


def setup_telebot(token: str, chat_id: str) -> None:
    """
    Set up the Telegram bot with the provided token and chat ID.
    """
    global _bot
    _bot = TeleBot(token, chat_id)
    logger.info("Telegram bot initialized.")


def get_telebot() -> TeleBot:
    """
    Get the initialized singleton Telegram bot.
    """
    if _bot is None:
        raise ValueError(
            "Telegram bot not initialized. Call setup_telebot first."
        )
    return _bot
