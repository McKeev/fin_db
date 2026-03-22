"""
File Name: execute.py
Author: Cedric McKeever
Date: 2026-03-13
Description:
This module executes queries found in this submodule.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
from typing import Any
import logging
# Third Party Imports
from psycopg import sql  # pyright: ignore[reportMissingImports]
# Local Imports
from fin_db.constants import ROOT_DIR, SOURCE_IDENTIFIERS
from fin_db.session import db_conn

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------


_IDENTIFIER_TYPES: set[str] | None = None  # Lazy load
QUERIES = ROOT_DIR / 'queries'


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


def query_read(
    query_file: str,
    params: dict[str, Any] | tuple[Any, ...] | None = None,
    identifiers: dict[str, str] | None = None
) -> list[tuple[Any, ...]]:
    """
    Execute a SQL query from a file.

    Parameters
    ----------
    query_file : str
        The name of the SQL file containing the query to execute.
    params : dict[str, Any] | tuple[Any, ...] | None, optional
        Parameters to pass to the query, by default None.
    identifiers : dict[str, str] | None, optional
        Identifiers to pass to the query, by default None.
    """
    with open(QUERIES / query_file, 'r') as f:
        query_text = f.read()
    query_obj = sql.SQL(query_text)
    if identifiers:
        # Add identifiers to the query using psycopg's SQL composition
        query_obj = query_obj.format(
            **{k: sql.Identifier(v) for k, v in identifiers.items()}
        )
    with db_conn().cursor() as cur:
        cur.execute(query_obj, params)
        logger.debug(f"Executed query from {query_file} with params: {params}")
        return cur.fetchall()


def to_update(
    frequency: str = 'daily',
    source: str = 'YAHOO'
) -> dict[tuple[str, ...], list[str]]:
    """
    Get a list of updates to perform, grouped by instrument.

    Parameters
    ----------
    frequency : str, optional
        The frequency of the updates to retrieve (e.g., 'daily', 'weekly'),
        by default 'daily'.
    source : str, optional
        The source of the updates to retrieve (e.g., 'YAHOO', 'LSEG'),
        by default 'YAHOO'.

    Returns
    -------
    dict[tuple[str, ...], list[str]]
        A dictionary where the keys are tuples of fields to update with
        corresponding tickers as values.
    """

    if source not in SOURCE_IDENTIFIERS:
        raise ValueError(
            f"Unsupported source: {source}. "
            f"Supported sources are: {list(SOURCE_IDENTIFIERS.keys())}"
        )
    result = query_read(
        'updates_list.sql',
        params={
            'frequency': frequency,
            'source': source,
        },
        identifiers={
            'identifier_col': SOURCE_IDENTIFIERS[source]
        }
    )
    result_dict = {
        # Convert lists of fields to tuples
        tuple(k) if isinstance(k, list) else (k,): v
        for k, v in result
    }
    return result_dict


def get_iid_mapping(
    tickers: str | list[str],
    identifier_type: str
) -> dict[str, str]:
    """
    Get internal `instrument_id`s for a list of external tickers.

    Parameters
    ----------
    tickers : str | list[str]
        A single ticker or a list of tickers to translate.
    identifier_type : str
        The type of identifier provided (e.g., 'yfin', 'ric').

    Returns
    -------
    dict[str, str]
        A dictionary mapping external tickers to internal `instrument_id`s.
    """
    global _IDENTIFIER_TYPES
    # Get identier types if needed
    if _IDENTIFIER_TYPES is None:
        with db_conn().cursor() as cur:
            cur.execute(
                "SELECT column_name"
                " FROM information_schema.columns"
                " WHERE table_name = 'identifiers'"
                "  AND table_schema = 'public';"
            )
            _IDENTIFIER_TYPES = {row[0] for row in cur.fetchall()}

    # Checks and normalization
    if identifier_type not in _IDENTIFIER_TYPES:
        raise ValueError(
            f"Unsupported identifier type: {identifier_type}. "
            f"Supported types are: {_IDENTIFIER_TYPES}"
        )
    if isinstance(tickers, str):
        tickers = [tickers]

    result = query_read(
        'instrument_id_mapping.sql',
        params={'tickers': tickers},
        identifiers={'identifier': identifier_type}
    )
    return {row[0]: row[1] for row in result}


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    pass
