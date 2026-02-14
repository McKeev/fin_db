"""
File Name: yfin_puller.py
Author: Cedric McKeever
Date: 2026-02-13
Description:
Stores content related to pulling data from yfinance
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
import datetime as dt
import logging
import time
import math
# Third Party Imports
import pandas as pd
import yfinance as yf
# Local Imports
from fin_db.constants import FIELDS

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------


SLEEP = 3  # seconds to wait between retries


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------


class YFinPuller:
    def __init__(
        self,
        tickers: list,
        sdate: str,
        edate: str,
        batch_size: int = 5,
        max_retries: int = 5,
    ):
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
        built-in batching and retry logic and data validation to handle yfin
        API issues.

        Parameters:
        -----------
        fields: str | list[str]
            The field(s) to pull (e.g. 'close', 'totret').

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the pulled data (long format), with columns
            for date, identifier, source, field, scale, and value.
        """
        if isinstance(fields, str):
            fields = [fields]
        for f in fields:
            if f not in FIELDS.keys():
                raise ValueError(f"Field '{f}' not supported.")

        frames = []

        for i, batch in enumerate(self.batches):
            logger.info(f"Pulling batch {i + 1} of "
                        f"{len(self.batches)}: {batch}")

            try:
                data = self._yfin_pull(batch, fields)
                frames.append(data)
                logger.debug(f"Successfully pulled data for batch {i + 1}")
                time.sleep(SLEEP)  # brief pause between batches

            except RuntimeError as e:
                logger.error(f"Failed to pull data for batch {i + 1}: {e}")
                continue

        return pd.concat(frames, ignore_index=True)

    def _yfin_pull(self, tickers: list, fields: list) -> pd.DataFrame:
        """
        Pull fields for a list of tickers.
        Check `download_and_process` function for how we handle pull.
        Rest of function is retry logic and error handling.
        """

        def download_and_process():
            if 'totret' in fields:
                sdate = self.sdate - dt.timedelta(days=1)
            else:
                sdate = self.sdate
            data = yf.download(
                tickers=tickers,
                start=sdate,
                end=self.edate,
                auto_adjust=False,
                actions=True,
                progress=False,
            )
            # Basic validation to check if data looks correct
            if data.empty or data.isna().all().all():
                raise ValueError("Downloaded data is empty or all NaN.")
            for ticker in tickers:
                # Extract data for the specific ticker (flattens)
                ticker_data = data.xs(ticker, level=1, axis=1).copy()

                # Need to calc close if requested
                if 'close' in fields:
                    # Calculate split multiplier from 'Stock Splits' column
                    ticker_data['split_mult'] = (
                        ticker_data['Stock Splits'].shift(-1).fillna(1)
                        .replace(0, 1)
                        .iloc[::-1].cumprod().iloc[::-1]  # Reverse cumprod
                    )
                    ticker_data[FIELDS['close']['yfin']] = (
                        ticker_data['Close'] * ticker_data['split_mult']
                    )
                # Need to calc totret if requested
                if 'totret' in fields:
                    ticker_data[FIELDS['totret']['yfin']] = (
                        ticker_data['Adj Close'].pct_change() * 100
                    )
                    ticker_data = ticker_data.iloc[1:]  # Drop first row

                # only keep the fields we care about
                to_keep = [FIELDS[f]['yfin'] for f in fields]
                ticker_data = ticker_data[to_keep]

                # Rename to corresponding field names
                rename_dict = {
                    FIELDS[f]['yfin']: f for f in fields
                }
                rename_dict['Date'] = 'date'
                ticker_data = ticker_data.reset_index()
                ticker_data.rename(columns=rename_dict, inplace=True)

                ticker_long = (
                    ticker_data
                    .assign(identifier=ticker)
                    .melt(
                        id_vars=['date', 'identifier'],
                        value_vars=list(rename_dict.values()),
                        var_name='field',
                        value_name='value'
                    )
                    .assign(scale=lambda x: x['field'].map(
                        lambda f: FIELDS[f]['scale']
                    ))
                    .assign(source='YAHOO')
                    [[  # Reorder
                        'date', 'identifier', 'source',
                        'field', 'scale', 'value'
                    ]]
                )

                return ticker_long

        attempt = 1
        last_exception = None

        while attempt <= self.max_retries:
            try:
                return download_and_process()

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
