"""
File Name: constants.py
Author: Cedric McKeever
Date: 2026-02-13
Description:
Constants used throughout the fin_db package.
"""

from pathlib import Path
from typing import TypedDict

# Root directory of package
ROOT_DIR = Path(__file__).parent.parent.parent


class FieldConfig(TypedDict):
    """Configuration for a financial field across different data sources."""
    lseg: str
    yfin: str
    scale: float


FIELDS: dict[str, FieldConfig] = {
    'close': {
        'lseg': 'TR.CLOSEPRICE(Adjusted=0)',
        'yfin': 'raw_close',
        'scale': 1
    },
    'totret': {
        'lseg': 'TR.TotalReturn',
        'yfin': 'totret',
        'scale': 0.01
    }
}
