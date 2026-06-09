"""
File Name: async_session.py
Author: Cedric McKeever
Date: 2026-06-09
Description:
Async implementation of database connection management using psycopg's AsyncConnectionPool.
This provides automatic connection pooling, health checks, and automatic reconnection.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------

import logging
from typing import Optional

# Third Party Imports
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------

_pool: Optional[AsyncConnectionPool] = None


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


async def _create_pool(
    user: str,
    password: str | None = None,
    host: str = "minicomp",
    port: int = 5433,
    dbname: str = "fin_db",
    min_size: int = 10,
    max_size: int = 20,
) -> AsyncConnectionPool:
    """
    Create and return an async connection pool.

    The pool automatically manages connection lifecycle, including:
    - Reusing connections across requests
    - Detecting and replacing stale connections
    - Handling reconnection on failures
    - Managing timeouts and resource limits

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
    min_size : int, optional
        Minimum number of connections to maintain, by default 10.
    max_size : int, optional
        Maximum number of connections, by default 20.

    Returns
    -------
    AsyncConnectionPool
        A connection pool ready to use.

    Raises
    ------
    psycopg.OperationalError
        If connection to database fails.
    """
    conninfo = (
        f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        if password
        else f"postgresql://{user}@{host}:{port}/{dbname}"
    )

    pool = AsyncConnectionPool(
        conninfo,
        min_size=min_size,
        max_size=max_size,
        connection_class=AsyncConnection,
        open=False,
        # Connection settings
        kwargs={
            "connect_timeout": "10",
            "keepalives": "1",
            "keepalives_idle": "30",
        },
    )

    logger.info(
        f"Connection pool created: {min_size}-{max_size} connections "
        f"to {host}:{port}/{dbname}"
    )

    return pool


async def open_pool(
    user: str,
    password: str | None = None,
    host: str = "minicomp",
    port: int = 5433,
    dbname: str = "fin_db",
    min_size: int = 10,
    max_size: int = 20,
) -> None:
    """
    Initialize the global async connection pool.

    Call this once at application startup (e.g., in your Telegram bot's startup handler).

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
    min_size : int, optional
        Minimum pool size, by default 10.
    max_size : int, optional
        Maximum pool size, by default 20.

    Raises
    ------
    Exception
        If a pool is already open.
    psycopg.OperationalError
        If connection to database fails.

    Example
    -------
    >>> import fin_db as fdb
    >>> await fdb.open_pool(user="user", password="pass")
    """
    global _pool
    if _pool is not None:
        raise Exception(
            "A connection pool is already open. "
            "Please close it before opening a new one."
        )

    _pool = await _create_pool(
        user=user,
        password=password,
        host=host,
        port=port,
        dbname=dbname,
        min_size=min_size,
        max_size=max_size,
    )
    await _pool.open()
    logger.info("Global connection pool opened successfully.")


def get_pool() -> AsyncConnectionPool:
    """
    Get the global async connection pool.

    Returns
    -------
    AsyncConnectionPool
        The global connection pool.

    Raises
    ------
    Exception
        If no pool is open.

    Example
    -------
    >>> pool = get_pool()
    >>> async with await pool.connection() as conn:
    ...     async with conn.cursor() as cur:
    ...         await cur.execute("SELECT 1")
    """
    if _pool is None:
        raise Exception(
            "No connection pool is open. "
            "Please open a pool first (`await open_pool()`)."
        )
    return _pool


async def close_pool() -> None:
    """
    Close the global async connection pool.

    Call this when shutting down your application (e.g., in Telegram bot's shutdown handler).

    Example
    -------
    >>> await close_pool()
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed successfully.")
