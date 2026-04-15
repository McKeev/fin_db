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
from psycopg import sql
import pandas as pd
# Local Imports
from fin_db.constants import ROOT_DIR
from fin_db.session import db_conn
from fin_db.helpers import valid_sources, to_datetime, DateLike

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------


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
    with open(QUERIES / 'read' / query_file, 'r') as f:
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


def query_write(
    query_file: str,
    params: dict[str, Any] | list[dict[str, Any]] | None = None,
    identifiers: dict[str, str] | None = None,
    commit: bool = True
) -> None:
    """
    Execute a SQL write query from a file.

    Parameters
    ----------
    query_file : str
        The name of the SQL file containing the query to execute.
    params : dict[str, Any] | tuple[Any, ...] | None, optional
        Parameters to pass to the query, by default None.
    identifiers : dict[str, str] | None, optional
        Identifiers to pass to the query, by default None.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    with open(QUERIES / 'write' / query_file, 'r') as f:
        query_text = f.read()
    query_obj = sql.SQL(query_text)
    if identifiers:
        # Add identifiers to the query using psycopg's SQL composition
        query_obj = query_obj.format(
            **{k: sql.Identifier(v) for k, v in identifiers.items()}
        )
    with db_conn().cursor() as cur:
        if isinstance(params, list):
            cur.executemany(query_obj, params)
        else:
            cur.execute(query_obj, params)
        logger.info(
            f"Executed write query from {query_file} "
            f"({cur.rowcount} rows affected)."
        )
        if commit:
            db_conn().commit()
            logger.info("Transaction committed.")
        else:
            db_conn().rollback()
            logger.info("Transaction rolled back.")


# ------------------------------- READ QUERIES --------------------------------


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
    dict[tuple[str, tuple[str, ...]], list[str]]
        A dictionary where the keys are tuples of asset classes and field sets
        to update with corresponding tickers as values.
    """

    if source not in valid_sources():
        raise ValueError(
            f"Unsupported source: {source}. "
            f"Supported sources are: {list(valid_sources())}"
        )
    result = query_read(
        'updates_list.sql',
        params={
            'frequency': frequency,
            'source': source,
        },
    )
    result_dict = {
        (
            asset_class, tuple(fields)
            if isinstance(fields, list) else (fields,)
        ): tickers
        for asset_class, fields, tickers in result
    }
    return result_dict


def get_iid_mapping(
    tickers: str | list[str],
    source: str
) -> dict[str, str]:
    """
    Get internal `instrument_id`s for a list of external tickers.

    Parameters
    ----------
    tickers : str | list[str]
        A single ticker or a list of tickers to translate.
    source : str
        The source of the identifiers (e.g., 'YAHOO', 'ISIN').

    Returns
    -------
    dict[str, str]
        A dictionary mapping external tickers to internal `instrument_id`s if
        found in the database. If a ticker is not found, it will show None.
        Example: {'AAPL': '12345', 'GOOG': '67890', 'MADEUP': None}
    """
    # Checks and normalization
    if source not in valid_sources():
        raise ValueError(
            f"Unsupported source: {source}. "
            f"Supported sources are: {list(valid_sources())}"
        )
    # Precaution bc etoro API can return int for id
    if type(tickers) is not list:
        tickers = [str(tickers)]
    tickers = [str(ticker) for ticker in tickers]

    result = query_read(
        'instrument_id_mapping.sql',
        params={
            'tickers': tickers,
            'source': source
        }
    )
    return {row[0]: row[1] for row in result}


def check_updates(
    cutoff_date: str
) -> list[dict[str, Any]]:
    """
    Check which instruments have not been updated after cutoff date.

    Parameters
    ----------
    cutoff_date : str
        The cutoff date in 'YYYY-MM-DD' format. Instruments with last updates
        older (<=) than this date will be returned.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries containing `instrument_id`, `name`, `field`, and
        `last_update` of concerned instruments.
    """
    result = query_read(
        'check_updates.sql',
        params={'cutoff_date': cutoff_date}
    )
    return [
        {
            'instrument_id': row[0],
            'name': row[1],
            'field': row[2],
            'last_update': row[3]
        }
        for row in result
    ]


def hist(
    tickers: str | list[str],
    fields: str | list[str],
    sdate: DateLike,
    edate: DateLike,
) -> pd.DataFrame:
    """
    Get historical data for a list of tickers and fields between two dates.

    Parameters
    ----------
    tickers : str | list[str]
        A single ticker or a list of tickers to retrieve data for.
    fields : str | list[str]
        A single field or a list of fields to retrieve ('price', 'totret', ..).
    sdate : DateLike
        The start date for which to retrieve data.
    edate : DateLike
        The end date for which to retrieve data.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the historical data for the specified tickers
        and fields, indexed by date with multi-level columns for ticker and
        field.
    """
    # Normalize inputs
    if type(tickers) is not list:
        tickers = [str(tickers)]
    if type(fields) is not list:
        fields = [str(fields)]
    sdate = to_datetime(sdate)
    edate = to_datetime(edate)

    result = query_read(
        'usd_ts.sql',
        params={
            'tickers': tickers,
            'fields': fields,
            'sdate': sdate.date().isoformat(),
            'edate': edate.date().isoformat()
        }
    )
    logger.debug('Query read')

    # Long format df
    df = pd.DataFrame(result, columns=['ticker', 'field', 'date', 'value'])
    # Create multi-index DataFrame with columns for ticker-fields
    df = df.pivot_table(
        index='date',
        columns=['ticker', 'field'],
        values='value'
    )

    return df


# ------------------------------ WRITE QUERIES --------------------------------


def ingest_observations(
    df: pd.DataFrame,
    commit: bool = True
) -> None:
    """
    Ingest a DataFrame of observations into the database.
    CAUTION:
    This function does not perform any validation or transformation on the
    data, so it assumes that the DataFrame is already in the correct format for
    ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the observations to ingest.
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    # Write to DB
    query_write(
        'write_observations.sql',
        params=df.to_dict(orient='records'),
        commit=commit
    )
    # Log the successful updates into `updates`
    query_write(
        'log_updates.sql',
        params=(
            df[['instrument_id', 'field', 'source']]
            .drop_duplicates()
            .to_dict(orient='records')
        ),
        commit=commit
    )


def log_failed_ingest(
    df: pd.DataFrame,
    commit: bool = True
) -> None:
    """
    Log failed ingestions into the database.
    CAUTION:
    This function does not perform any validation or transformation on the
    data, so it assumes that the DataFrame is already in the correct format for
    ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the failed ingestions to log. Must contain
        columns `instrument_id`, `field`, `source`, and `error_message`.
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    # Write to DB
    query_write(
        'write_fails.sql',
        params=df.to_dict(orient='records'),
        commit=commit
    )


def ingest_instruments(
    df: pd.DataFrame,
    commit: bool = True
) -> None:
    """
    Ingest a DataFrame of instruments into the database.
    CAUTION:
    This function does not perform any validation or transformation on the
    data, so it assumes that the DataFrame is already in the correct format for
    ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the instruments to ingest. Must contain
        columns `instrument_id`, `name`, `asset_class`, `unit`, and
        `internal_ticker`.
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    query_write(
        'write_instruments.sql',
        params=df.to_dict(orient='records'),
        commit=commit
    )


def ingest_attributes(
    df: pd.DataFrame,
    commit: bool = True
) -> None:
    """
    Ingest a DataFrame of attributes into the database.
    CAUTION:
    This function does not perform any validation or transformation on the
    data, so it assumes that the DataFrame is already in the correct format for
    ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the attributes to ingest. Must contain columns
        `instrument_id`, `field`, and `value`.
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    query_write(
        'write_attributes.sql',
        params=df.to_dict(orient='records'),
        commit=commit
    )


def ingest_updates(
    df: pd.DataFrame,
    commit: bool = True
) -> None:
    """
    Ingest a DataFrame of updates into the database.
    CAUTION:
    This function does not perform any validation or transformation on the
    data, so it assumes that the DataFrame is already in the correct format for
    ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the updates to ingest. Must contain columns
        `instrument_id`, `field`, `source`, and `frequency` (date auto-set).
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    # Write to DB
    query_write(
        'write_updates.sql',
        params=df.to_dict(orient='records'),
        commit=commit
    )


def ingest_identifiers(
    df: pd.DataFrame,
    commit: bool = True
) -> None:
    """
    Ingest a DataFrame of identifiers into the database.
    CAUTION:
    This function does not perform any validation or transformation on the
    data, so it assumes that the DataFrame is already in the correct format for
    ingestion.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the identifiers to ingest. Must contain
        columns `instrument_id`, `source`, and `external_id`.
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    query_write(
        'write_identifiers.sql',
        params=df.to_dict(orient='records'),
        commit=commit
    )


def refresh_portfolios_obs(
    commit: bool = True
) -> None:
    """
    Refresh portfolio observations based on holdings and prices.

    Parameters
    ----------
    commit : bool, optional
        Whether to commit the transaction, by default True.

    Returns
    -------
    None
    """
    query_write(
        'refresh_portfolios.sql',
        commit=commit
    )
