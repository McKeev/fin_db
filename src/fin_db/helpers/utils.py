"""
File Name: utils.py
Author: Cedric McKeever
Date: 2026-03-25
Description:
Easy helpers for general use across the package.
"""

# First Party Imports
import time
import re
# Third Party Imports
from datetime import datetime, date, timedelta
from dateutil import parser as dateutil_parser
import numpy as np
import pandas as pd
# Local Imports
from fin_db.session import db_conn


# =============================================================================
# ================================== SOURCES ==================================
# =============================================================================
_SOURCES: set[str] | None = None  # Lazy load


def valid_sources() -> set[str]:
    global _SOURCES
    if _SOURCES is None:
        with db_conn().cursor() as cur:
            cur.execute(
                "SELECT name FROM sources;"
            )
            _SOURCES = {row[0] for row in cur.fetchall()}
    return _SOURCES


# =============================================================================
# ================================ DATE STUFF =================================
# =============================================================================
class InvalidDateError(ValueError):
    def __init__(self, value):
        message = f"Invalid date provided: {value!r}"
        super().__init__(message)


DateLike = (
    datetime | date | int | float | time.struct_time | timedelta |
    str | np.datetime64 | pd.Timestamp
)


def to_datetime(
    value: DateLike,
    dayfirst=False
) -> datetime:
    """
    Convert almost anything to a datetime object.
    Accepts: datetime, date, int/float (unix timestamp), struct_time,
             timedelta (offset from now), string (any format).

    Parameters:
    -----------
    value: DateLike
        The value to convert to datetime.
    dayfirst: bool, default False
        If True, will interpret ambiguous date strings like "01/02/2020" as
        1st Feb 2020 instead of Jan 2nd. Passed to dateutil.parser.parse() when
        parsing strings.

    Returns:
    --------
    datetime
         The converted datetime object.

    Raises:
    -------
    InvalidDateError
        If the value cannot be parsed as a date.
    """

    # Already a datetime — return as-is
    if isinstance(value, datetime):
        return value

    # date (but not datetime, since datetime is a subclass of date)
    if type(value) is date:
        return datetime(value.year, value.month, value.day)

    # Unix timestamp (int or float)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)

    # time.struct_time (returned by time.localtime(), time.gmtime(), etc.)
    if isinstance(value, time.struct_time):
        return datetime(*value[:6])

    # timedelta — interpret as offset from now
    if isinstance(value, timedelta):
        return datetime.now() + value

    # numpy datetime64
    if isinstance(value, np.datetime64):
        ts = (
            (value - np.datetime64("1970-01-01T00:00:00"))
            / np.timedelta64(1, "s")
        )
        return datetime.fromtimestamp(ts, tz=time.timezone.utc)

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    # pandas NaT
    if value is pd.NaT:
        raise InvalidDateError(value)

    # String — try dateutil then manual formats
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise InvalidDateError(value)
        # Strip ordinal suffixes: "15th" → "15"
        cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", value)
        try:
            return dateutil_parser.parse(cleaned, dayfirst=dayfirst)
        except (ValueError, OverflowError):
            pass

    raise InvalidDateError(value)


# =============================================================================
# ================================ DECORATORS ================================
# =============================================================================
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper
