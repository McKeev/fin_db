"""
File Name: async_session.py
Author: Cedric McKeever
Date: 2026-03-13
Description:
Async implementation of database connection management using psycopg's async support.
Implements a singleton async connection pool for use in async contexts.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------

import logging
from typing import Optional

# Third Party Imports
import psycopg

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------

_async_conn: Optional[psycopg.AsyncConnection] = None


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


async def open_async_session(
    user: str,
    password: str | None = None,
    host: str = "minicomp",
    port: int = 5433,
    dbname: str = "fin_db",
) -> None:
    """
    Open a new async database session.

    This creates a global async connection that can be used for async/await
    database operations. Use this in your async startup code.

    Parameters
    ----------
    user : str
        Database user.
    password : str | None, optional
        Database password, by default None.
    host : str, optional
        Database host, by default "minicomp".
    port : int, optional
        Database port, by default 5433.
    dbname : str, optional
        Database name, by default "fin_db".

    Raises
    ------
    Exception
        If a session is already open.
    """
    global _async_conn
    if _async_conn is not None:
        raise Exception(
            "An async session is already open. "
            "Please close it before opening a new one."
        )
    _async_conn = await psycopg.AsyncConnection.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    logger.info("Async database session opened successfully.")


async def async_db_conn() -> psycopg.AsyncConnection:
    """
    Get the current async database connection.

    Returns
    -------
    psycopg.AsyncConnection
        The global async connection.

    Raises
    ------
    Exception
        If no async session is open.
    """
    if _async_conn is None:
        raise Exception(
            "No async session is open. "
            "Please open a session first (`await open_async_session()`)."
        )
    return _async_conn


async def close_async_session() -> None:
    """
    Close the async database session.
    """
    global _async_conn
    if _async_conn is not None:
        await _async_conn.aclose()
        _async_conn = None
        logger.info("Async database session closed successfully.")


# Context manager for temporary async connections (alternative to global state)
class AsyncSessionContext:
    """
    Context manager for async database connections.

    Usage:
    ------
    async with AsyncSessionContext(user="user", password="pass") as conn:
        # Use conn for queries
        pass
    """

    def __init__(
        self,
        user: str,
        password: str | None = None,
        host: str = "minicomp",
        port: int = 5433,
        dbname: str = "fin_db",
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.dbname = dbname
        self.conn: Optional[psycopg.AsyncConnection] = None

    async def __aenter__(self) -> psycopg.AsyncConnection:
        self.conn = await psycopg.AsyncConnection.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn is not None:
            await self.conn.aclose()


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    pass
