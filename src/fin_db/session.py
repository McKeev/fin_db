"""
File Name: session.py
Author: Cedric McKeever
Date: 2026-03-13
Description:
Implementing a singleton approach for database connection.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------


# First Party Imports
import logging
# Third Party Imports
import psycopg
# Local Imports

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------


_conn: psycopg.Connection | None = None


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


def open_session(
    user: str,
    password: str | None = None,
    host: str = 'minicomp',
    port: int = 5433,
    dbname: str = 'fin_db',
) -> None:
    """
    Open a new database session.
    """
    global _conn
    if _conn is not None:
        raise Exception(
            'A session is already open. '
            'Please close it before opening a new one.'
        )
    _conn = psycopg.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
    )
    logger.info('Database session opened successfully.')


def db_conn() -> psycopg.Connection:
    """
    Get the current database connection.
    """
    if _conn is None:
        raise Exception(
            'No session is open. '
            'Please open a session first (`open_session()`).')
    return _conn


def close_session() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
        logger.info('Database session closed successfully.')


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    pass
