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
        max_attempts: int = 5,
    ):
        self.tickers = tickers
        self.sdate = dt.datetime.strptime(sdate, "%Y-%m-%d")
        self.edate = dt.datetime.strptime(edate, "%Y-%m-%d")
        self.batch_size = batch_size
        self.max_attempts = max_attempts

    def histpull(
        self,
        fields: str | list[str],
        return_failed: bool = False
    ) -> pd.DataFrame | tuple[pd.DataFrame, list[str]]:
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
            for 'identifier', 'field', 'date', 'source', 'value' and 'scale'.
        list[str]
            If return_failed is True, also returns a list of tickers for which
            the pull failed (e.g. due to API issues).
        """
        if isinstance(fields, str):
            fields = [fields]
        for f in fields:
            if f not in FIELDS.keys():
                raise ValueError(f"Field '{f}' not supported.")

        frames = []
        batches = self._split_batches(self.tickers)

        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Attempt {attempt} of {self.max_attempts}")
            failed_tickers = []

            for i, batch in enumerate(batches):
                logger.info(f"Pulling batch {i + 1} of "
                            f"{len(batches)}: {batch}")
                try:
                    data, failed = self._yfin_pull(batch, fields)
                    frames.append(data)
                    logger.debug(f"Successfully pulled data for batch {i + 1}")
                    time.sleep(SLEEP)  # brief pause between batches
                    failed_tickers.extend(failed)
                except Exception as e:
                    logger.error(
                        f"Error occurred while pulling data for batch {i + 1}:"
                        f" {e}"
                    )
                    failed_tickers.extend(batch)  # consider whole batch failed
            if not failed_tickers:
                logger.info("All tickers pulled successfully.")
                break
            else:
                logger.warning(
                    f"Failed to pull data for tickers: {failed_tickers}"
                    f" - Retrying failed tickers in next attempt."
                )
                batches = self._split_batches(failed_tickers)
                time.sleep(SLEEP * 2)  # longer pause before retrying failed
        # Return empty DataFrame if all attempts failed
        if not frames:
            empty = pd.DataFrame(
                columns=[
                    'identifier', 'field', 'date', 'source', 'value', 'scale'
                ]
            )
            return (empty, failed_tickers) if return_failed else empty
        if return_failed:
            return pd.concat(frames, ignore_index=True), failed_tickers
        else:
            return pd.concat(frames, ignore_index=True)

    def _yfin_pull(
        self,
        tickers: list,
        fields: list
    ) -> tuple[pd.DataFrame, list[str]]:
        """
        Pull fields for a list of tickers.

        Parameters:
        -----------
        tickers: list
            List of tickers to pull.
        fields: list
            List of fields to pull (e.g. 'close', 'totret').

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing the pulled data (long format), with columns
            for 'identifier', 'field', 'date', 'source', 'value' and 'scale'.
        list
            List of tickers for which the pull failed (e.g. due to API issues).
        """

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
            multi_level_index=True,
            threads=False  # Slower but more reliable for large batches
        )
        # Basic validation to check if data looks correct
        if data.empty or data.isna().all().all():
            raise ValueError("No data available for any requested tickers.")

        successes = []
        failed = []
        for ticker in tickers:
            # Extract data for the specific ticker (flattens)
            try:
                ticker_data = data.xs(ticker, level=1, axis=1)
                successes.append(
                    self._process_ticker(ticker, ticker_data, fields)
                )
            except Exception as e:
                logger.error(f"Error processing ticker '{ticker}': {e}")
                failed.append(ticker)
                continue

        if not successes:
            raise ValueError("All tickers failed to pull or process.")
        return pd.concat(successes, ignore_index=True), failed

    @staticmethod
    def _process_ticker(
        ticker: str,
        ticker_data: pd.DataFrame,
        fields: list
    ) -> pd.DataFrame:
        """
        Process raw data for a single ticker, calculating necessary fields and
        reshaping to long format.

        Parameters:
        -----------
        ticker: str
            The ticker being processed.
        ticker_data: pd.DataFrame
            Raw data for a single ticker, with columns like 'Close',
            'Adj Close', 'Stock Splits', etc.
        fields: list
            List of fields to pull (e.g. 'close', 'totret').

        Returns:
        --------
        pd.DataFrame
            Processed data for the ticker in long format, with columns for
            'identifier', 'field', 'date', 'source', 'value' and 'scale'.
        """
        ticker_data = ticker_data.copy()  # mutability
        # Drop rows where close is NaN, as these are likely non-trading days
        ticker_data = ticker_data.dropna(
            subset=['Close', 'Adj Close'], how='all'
        )
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
                ticker_data['Adj Close'].pct_change(fill_method=None) * 100
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
                value_vars=fields,
                var_name='field',
                value_name='value'
            )
            .assign(scale=lambda x: x['field'].map(
                lambda f: FIELDS[f]['scale']
            ))
            .assign(source='YAHOO')
            [[  # Reorder
                'identifier', 'field', 'date',
                'source', 'value', 'scale'
            ]]
        )
        if ticker_long.empty or ticker_long.isna().all().all():
            raise ValueError(
                f"Processed data for ticker '{ticker}' is empty or all NaN."
            )
        return ticker_long

    def _split_batches(
        self,
        tickers: list
    ) -> list:
        batches = []
        """Split tickers into batches."""
        for i in range(0, math.ceil(len(tickers) / self.batch_size)):
            end = min((i+1) * self.batch_size, len(tickers))
            batches.append(tickers[i * self.batch_size:end])
        return batches


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    pass
