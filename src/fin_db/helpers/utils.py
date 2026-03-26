"""
File Name: utils.py
Author: Cedric McKeever
Date: 2026-03-25
Description:
Easy helpers for general use across the package.
"""

# Imports
from fin_db.session import db_conn


# For retrieving acceptable sources
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
