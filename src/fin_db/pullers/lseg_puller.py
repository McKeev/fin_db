"""
File Name: lseg_puller.py
Author: Cedric McKeever
Date: 2026-02-03
Description:
Insert description here
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
import datetime as dt
import logging
import time
import math
import warnings
# Third Party Imports
try:
    import refinitiv.data as rd
except ImportError:  # pragma: no cover
    rd = None
import pandas as pd
# Local Imports
from fin_db.constants import FIELDS

# Silence warnings from external packages
warnings.filterwarnings('ignore', category=FutureWarning, module='refinitiv')

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------


SLEEP = 3  # seconds to wait between retries


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------


class LSEGPuller:
    def __init__(
        self,
        tickers: list,
        sdate: str,
        edate: str,
        batch_size: int = 5,
        max_retries: int = 5,
    ):
        # Safeguard against missing refinitiv-data dependency
        if rd is None:
            raise ImportError(
                "refinitiv-data is required to use LSEGPuller. "
                "Install it with: poetry install --with refinitiv"
            )

        self.tickers = tickers
        self.sdate = dt.datetime.strptime(sdate, "%Y-%m-%d")
        self.edate = dt.datetime.strptime(edate, "%Y-%m-%d")
        self.batch_size = batch_size
        self.batches = self._split_batches()
        self.max_retries = max_retries

    def histpull(
        self,
        fields: str | list[str]
    ) -> pd.DataFrame:
        """
        Allows pulling historical data for a list of tickers and fields, with
        built-in batching and retry logic and data validation to handle LSEG
        API issues.

        Parameters:
        -----------
        fields: str | list[str]
            The field(s) to pull (e.g. 'close', 'totret').

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the pulled data (long format), with columns
            for date, identifier, field, scale, and value.
        """
        if isinstance(fields, str):
            fields = [fields]
        for f in fields:
            if f not in FIELDS.keys():
                raise ValueError(f"Field '{f}' not supported.")

        frames = []
        for field in fields:
            logger.info(f"Pulling '{field}' for {len(self.tickers)} tickers "
                        f"from {self.sdate.date()} to {self.edate.date()}")

            for i, batch in enumerate(self.batches):
                logger.info(f"Pulling batch {i + 1} of "
                            f"{len(self.batches)}: {batch}")

                try:
                    data = self._LSEG_pull(batch, field)
                    frames.append(data)
                    logger.debug(f"Successfully pulled data for batch {i + 1}")
                    time.sleep(SLEEP)  # brief pause between batches

                except RuntimeError as e:
                    logger.error(f"Failed to pull data for batch {i + 1}: {e}")
                    continue

        return pd.concat(frames, ignore_index=True)

    def _LSEG_pull(self, tickers: list, field: str) -> pd.DataFrame:
        """Pull field for a list of tickers."""

        attempt = 1
        last_exception = None

        while attempt <= self.max_retries:
            try:
                data = rd.get_history(
                    universe=tickers,
                    fields=[FIELDS[field]['lseg']],
                    start=self.sdate,
                    end=self.edate,
                    interval='daily',
                )
                if self._validate_lseg_data(data, tickers):
                    data = (
                        data.melt(
                            ignore_index=False,
                            var_name='RIC',
                            value_name='value'
                        )
                        .dropna()
                        .reset_index()
                        .assign(field=field)
                        .assign(source='LSEG')
                        .assign(scale=FIELDS[field]['scale'])
                        [['Date', 'RIC', 'source', 'field', 'scale', 'value']]
                    )
                    data = data.rename(columns={
                        'Date': 'date', 'RIC': 'identifier'
                    })
                    return data
                else:
                    logger.warning(
                        f"Data validation failed for {tickers} "
                        f"on attempt {attempt}."
                    )
                    time.sleep(SLEEP)
                    attempt += 1
                    continue

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Error pulling data for {tickers}: {e}"
                )
                time.sleep(SLEEP)
                attempt += 1
                continue
        logger.error(
            f"Failed to pull valid data for {tickers} after "
            f"{self.max_retries} attempts."
        )
        # Raise the last exception encountered for better debugging
        raise RuntimeError(
            f"Failed to pull valid data for {tickers} after "
            f"{self.max_retries} attempts."
        ) from last_exception

    def _validate_lseg_data(self, data: pd.DataFrame, tickers) -> bool:
        """Validate LSEG data quality."""
        if data is None or data.empty:
            logger.warning("No data returned.")
            return False

        if data.shape[1] != len(tickers):
            logger.warning(
                f"Expected {len(tickers)} columns, got {data.shape[1]}."
            )
            return False

        # Check each column has some valid values
        invalid_cols = [
            col for col in data.columns if data[col].notna().sum() == 0
        ]
        if invalid_cols:
            logger.warning(f"Columns with no valid data: {invalid_cols}.")
            return False

        return True

    def _split_batches(self) -> list:
        batches = []
        """Split tickers into batches."""
        for i in range(0, math.ceil(len(self.tickers) / self.batch_size)):
            end = min((i+1) * self.batch_size, len(self.tickers))
            batches.append(self.tickers[i * self.batch_size:end])
        return batches


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    pass
