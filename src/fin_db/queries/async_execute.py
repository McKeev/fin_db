"""
File Name: async_execute.py
Author: Cedric McKeever
Date: 2026-03-13
Description:
Async versions of query execution functions.
These functions are designed for use in async contexts (e.g., async Telegram bots).
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------

from typing import Any
import logging

# Third Party Imports
from psycopg import sql
import pandas as pd

# Local Imports
from fin_db.constants import ROOT_DIR
from fin_db.async_session import async_db_conn
from fin_db.helpers import valid_sources, to_datetime, DateLike

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------

QUERIES = ROOT_DIR / "queries"


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


async def query_read_async(
    query_file: str,
    params: dict[str, Any] | tuple[Any, ...] | None = None,
    identifiers: dict[str, str] | None = None,
) -> list[tuple[Any, ...]]:
    """
    Execute a SQL query from a file asynchronously.

    Parameters
    ----------
    query_file : str
        The name of the SQL file containing the query to execute.
    params : dict[str, Any] | tuple[Any, ...] | None, optional
        Parameters to pass to the query, by default None.
    identifiers : dict[str, str] | None, optional
        Identifiers to pass to the query, by default None.

    Returns
    -------
    list[tuple[Any, ...]]
        List of tuples containing the query results.
    """
    with open(QUERIES / "read" / query_file, "r") as f:
        query_text = f.read()
    query_obj = sql.SQL(query_text)
    if identifiers:
        # Add identifiers to the query using psycopg's SQL composition
        query_obj = query_obj.format(
            **{k: sql.Identifier(v) for k, v in identifiers.items()}
        )
    async with await async_db_conn().cursor() as cur:
        await cur.execute(query_obj, params)
        logger.debug(f"Executed async query from {query_file} with params: {params}")
        return await cur.fetchall()


async def query_write_async(
    query_file: str,
    params: dict[str, Any] | list[dict[str, Any]] | None = None,
    identifiers: dict[str, str] | None = None,
    commit: bool = True,
) -> None:
    """
    Execute a SQL write query from a file asynchronously.

    Parameters
    ----------
    query_file : str
        The name of the SQL file containing the query to execute.
    params : dict[str, Any] | list[dict[str, Any]] | None, optional
        Parameters to pass to the query, by default None.
    identifiers : dict[str, str] | None, optional
        Identifiers to pass to the query, by default None.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    with open(QUERIES / "write" / query_file, "r") as f:
        query_text = f.read()
    query_obj = sql.SQL(query_text)
    if identifiers:
        # Add identifiers to the query using psycopg's SQL composition
        query_obj = query_obj.format(
            **{k: sql.Identifier(v) for k, v in identifiers.items()}
        )
    conn = await async_db_conn()
    async with await conn.cursor() as cur:
        if isinstance(params, list):
            await cur.executemany(query_obj, params)
        else:
            await cur.execute(query_obj, params)
        logger.info(
            f"Executed async write query from {query_file} "
            f"({cur.rowcount} rows affected)."
        )
        if commit:
            await conn.commit()
            logger.info("Transaction committed.")
        else:
            await conn.rollback()
            logger.info("Transaction rolled back.")


# ------------------------------- READ QUERIES --------------------------------


async def get_iid_mapping_async(
    tickers: str | list[str], source: str
) -> dict[str, str]:
    """
    Get internal `instrument_id`s for a list of external tickers asynchronously.

    Parameters
    ----------
    tickers : str | list[str]
        A single ticker or a list of tickers to translate.
    source : str
        The source of the identifiers (e.g., 'YAHOO', 'ISIN').

    Returns
    -------
    dict[str, str]
        A dictionary mapping external tickers to internal `instrument_id`s.

    Raises
    ------
    ValueError
        If the source is not supported.
    """
    if source not in valid_sources():
        raise ValueError(
            f"Unsupported source: {source}. "
            f"Supported sources are: {list(valid_sources())}"
        )
    if type(tickers) is not list:
        tickers = [str(tickers)]
    tickers = [str(ticker) for ticker in tickers]

    result = await query_read_async(
        "instrument_id_mapping.sql",
        params={"tickers": tickers, "source": source},
    )
    return {row[0]: row[1] for row in result}


async def check_updates_async(cutoff_date: str) -> list[dict[str, Any]]:
    """
    Check which instruments have not been updated after cutoff date asynchronously.

    Parameters
    ----------
    cutoff_date : str
        The cutoff date in 'YYYY-MM-DD' format.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries containing instrument update information.
    """
    result = await query_read_async(
        "check_updates.sql", params={"cutoff_date": cutoff_date}
    )
    return [
        {
            "instrument_id": row[0],
            "name": row[1],
            "field": row[2],
            "last_update": row[3],
        }
        for row in result
    ]


async def resolve_instruments_async(
    raw_inputs: str | list[str],
) -> pd.DataFrame:
    """
    Resolve a list of raw input strings to instruments asynchronously.

    Parameters
    ----------
    raw_inputs : str | list[str]
        A single raw input string or a list of raw input strings to resolve.

    Returns
    -------
    pd.DataFrame
        A DataFrame with resolved instrument information.
    """
    if not isinstance(raw_inputs, list):
        raw_inputs = [str(raw_inputs)]
    result = await query_read_async(
        "resolve_instruments.sql", params={"raw_inputs": raw_inputs}
    )
    df = pd.DataFrame(
        result,
        columns=[
            "raw_input",
            "instrument_id",
            "internal_ticker",
            "name",
            "simpler_name",
            "asset_class",
            "name_score",
        ],
    )
    return df


async def get_hist_async(
    tickers: str | list[str],
    fields: str | list[str],
    sdate: DateLike,
    edate: DateLike,
) -> pd.DataFrame:
    """
    Get historical data for a list of tickers and fields asynchronously.

    This is the main async function you'll use in your Telegram bot.

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

    Raises
    ------
    ValueError
        If data for requested tickers is not found or date range is invalid.

    Example
    --------
    >>> async def get_stock_data(ticker):
    ...     await open_async_session(user="your_user", password="your_pass")
    ...     try:
    ...         data = await get_hist_async(ticker, "price", "2024-01-01", "2024-12-31")
    ...         return data
    ...     finally:
    ...         await close_async_session()
    """
    # Normalize inputs
    if type(tickers) is not list:
        tickers = [str(tickers)]
    if type(fields) is not list:
        fields = [str(fields)]
    sdate = to_datetime(sdate)
    edate = to_datetime(edate)

    result = await query_read_async(
        "usd_ts.sql",
        params={
            "tickers": tickers,
            "fields": fields,
            "sdate": sdate.date().isoformat(),
            "edate": edate.date().isoformat(),
        },
    )
    logger.debug("Async query read")

    # Long format df
    df = pd.DataFrame(result, columns=["ticker", "field", "date", "value"])

    # Check data
    if set(tickers) - set(df["ticker"].unique()):
        missing = set(tickers) - set(df["ticker"].unique())
        raise ValueError(f"Data for tickers {missing} not found in database.")
    elif df.empty:
        raise ValueError(
            "No data found for the specified tickers, fields, and date range."
        )

    # Create multi-index DataFrame with columns for ticker-fields
    df = df.pivot_table(
        index="date", columns=["ticker", "field"], values="value"
    )

    return df


async def to_update_async(
    frequency: str = "daily", source: str = "YAHOO"
) -> dict[tuple[str, ...], list[str]]:
    """
    Get a list of updates to perform, grouped by instrument asynchronously.

    Parameters
    ----------
    frequency : str, optional
        The frequency of the updates to retrieve, by default "daily".
    source : str, optional
        The source of the updates to retrieve, by default "YAHOO".

    Returns
    -------
    dict[tuple[str, ...], list[str]]
        A dictionary with update information grouped by asset class and fields.

    Raises
    ------
    ValueError
        If the source is not supported.
    """
    if source not in valid_sources():
        raise ValueError(
            f"Unsupported source: {source}. "
            f"Supported sources are: {list(valid_sources())}"
        )
    result = await query_read_async(
        "updates_list.sql",
        params={
            "frequency": frequency,
            "source": source,
        },
    )
    result_dict = {
        (
            asset_class,
            tuple(fields) if isinstance(fields, list) else (fields,),
        ): tickers
        for asset_class, fields, tickers in result
    }
    return result_dict


# ------------------------------ WRITE QUERIES --------------------------------


async def ingest_observations_async(df: pd.DataFrame, commit: bool = True) -> None:
    """
    Ingest a DataFrame of observations into the database asynchronously.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the observations to ingest.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async(
        "write_observations.sql",
        params=df.to_dict(orient="records"),
        commit=commit,
    )
    await query_write_async(
        "log_updates.sql",
        params=(
            df[["instrument_id", "field", "source"]]
            .drop_duplicates()
            .to_dict(orient="records")
        ),
        commit=commit,
    )


async def log_failed_ingest_async(df: pd.DataFrame, commit: bool = True) -> None:
    """
    Log failed ingestions into the database asynchronously.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the failed ingestions to log.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async(
        "write_fails.sql", params=df.to_dict(orient="records"), commit=commit
    )


async def ingest_instruments_async(df: pd.DataFrame, commit: bool = True) -> None:
    """
    Ingest a DataFrame of instruments into the database asynchronously.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the instruments to ingest.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async(
        "write_instruments.sql",
        params=df.to_dict(orient="records"),
        commit=commit,
    )


async def ingest_attributes_async(df: pd.DataFrame, commit: bool = True) -> None:
    """
    Ingest a DataFrame of attributes into the database asynchronously.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the attributes to ingest.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async(
        "write_attributes.sql",
        params=df.to_dict(orient="records"),
        commit=commit,
    )


async def ingest_updates_async(df: pd.DataFrame, commit: bool = True) -> None:
    """
    Ingest a DataFrame of updates into the database asynchronously.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the updates to ingest.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async(
        "write_updates.sql", params=df.to_dict(orient="records"), commit=commit
    )


async def ingest_identifiers_async(df: pd.DataFrame, commit: bool = True) -> None:
    """
    Ingest a DataFrame of identifiers into the database asynchronously.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the identifiers to ingest.
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async(
        "write_identifiers.sql",
        params=df.to_dict(orient="records"),
        commit=commit,
    )


async def refresh_portfolios_obs_async(commit: bool = True) -> None:
    """
    Refresh portfolio observations based on holdings and prices asynchronously.

    Parameters
    ----------
    commit : bool, optional
        Whether to commit the transaction, by default True.
    """
    await query_write_async("refresh_portfolios.sql", commit=commit)


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    pass
