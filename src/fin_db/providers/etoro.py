"""
File Name: etoro.py
Author: Cedric McKeever
Date: 2026-03-14
Description:
This script serves as an easier interface for the Etoro API
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
from typing import Any
import requests
import uuid
import logging
from pathlib import Path
import time
# Third Party Imports
import pandas as pd
import numpy as np
# Local Imports
from fin_db.helpers import to_datetime, DateLike
from fin_db.queries import get_iid_mapping

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------


# Sleep time between API calls to avoid rate limits (in seconds)
API_SLEEP = 1

# Used to transform the etoro acc statement
STATEMENT_COLS_MAP = {
    'Date': 'ts',
    'Type': 'type',
    'Position ID': 'position_id',
    'Details': 'instrument_id',
    'Units / Contracts': 'units',
    'fee': 'fee',
    'Amount': 'cashflow_usd'
}

STATEMENT_TYPES_MAP = {
    'Open Position': 'open',
    'Position closed': 'close',
    'Deposit': 'deposit',
    'Withdrawal': 'withdrawal',
    'Dividend': 'dividend',
    'Interest Payment': 'interest',
    'corp action: Split': 'split',
}


# ----------------------------------------------------------------------------
# ============================== CLASSES =====================================
# ----------------------------------------------------------------------------


class EtoroAPI:
    """
    Class to interact with the Etoro API.

    Attributes:
        keys (dict): A dictionary containing the API and user keys.
    """

    def __init__(
        self,
        x_api_key: str,
        x_user_key: str
    ):
        self.keys = {
            'api': x_api_key,
            'user': x_user_key
        }

    def search(
        self,
        lookup,
        field: str = 'instrumentId',
        return_fields: list[str] | None = None,
        ignore_internal: bool = True,
        strict: bool = False
    ) -> dict:
        """
        Searches for an instrument based on the provided lookup value and
        field. Key fields include:
        - 'instrumentId': The internal etoro instrument ID
        - 'internalSymbolFull': Full internal symbol
        - 'internalInstrumentDisplayName': The display name of the instrument
        - 'isin': The ISIN code of the instrument

        More info on the API endpoint here:
        https://api-portal.etoro.com/api-reference/
        market-data/search-for-instruments

        Parameters:
        -----------
        lookup : str or int
            The value to search for.
        field : str, optional
            The field to search in, by default 'instrumentId'.
        return_fields : list of str, optional
            A list of fields to return in the result. If None, returns all
            fields.
        ignore_internal : bool, default=True
            If True, ignores instruments with isInternalInstrument set to True.
        strict : bool, default=False
            If True, requires an exact match for the lookup value. If False,
            returns the first item that matches the lookup value in the
            specified field.

        Returns:
        --------
        dict
            The instrument data if found, otherwise raises an exception.
        """
        if field == 'instrumentId':
            # This field uses int to lookup
            try:
                lookup = int(lookup)
            except (ValueError, TypeError):
                raise ValueError(
                    "Lookup value for instrumentId "
                    "must be convertible to an integer"
                )
        if ignore_internal and strict:
            # This behaviour is acceptable considering usage of strict
            logger.warning(
                "Both ignore_internal and strict are set to True. "
                "Prioritizing strict search, which may return internal "
                "instruments (ignore_internal=False to silence this warning)."
            )

        url = "https://public-api.etoro.com/api/v1/market-data/search"
        params = {
            field: lookup
        }

        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code == 200:
            data = response.json()
            if strict:
                # Find the exact match in the returned items list
                instrument = next(
                    (item for item in data['items']
                     if item[field] == lookup), None
                )
            elif ignore_internal:
                # Return the first item from the search results
                instrument = next(
                    (item for item in data['items']
                     if item['isInternalInstrument'] is False), None
                )
            else:
                instrument = data['items'][0] if data['items'] else None

            if instrument and return_fields:
                return {key: instrument[key] for key in return_fields}
            elif instrument:
                return instrument
            else:
                raise Exception(
                    f"No instrument found for {lookup} in field {field}"
                )
        else:
            raise Exception(
                "API request failed with status code "
                f"{response.status_code}: {response.text}"
            )

    def trade_history(
        self,
        start_date: DateLike,
    ) -> list[dict]:
        """"
        Retrieves the trade history starting from the specified date.
        More info on the API endpoint here:
        https://api-portal.etoro.com/api-reference/
        trading--real/list-trading-history

        Parameters:
        -----------
        start_date : DateLike
            The starting date for retrieving trade history.

        Returns:
        --------
        list[dict]
            A list of dictionaries containing the historical trades data with
            the following format:
            {
                "netProfit": 123,
                "closeRate": 123,
                "closeTimestamp": "2023-11-07T05:31:56Z",
                "positionId": 123,
                "instrumentId": 123,
                "isBuy": true,
                "leverage": 123,
                "openRate": 123,
                "openTimestamp": "2023-11-07T05:31:56Z",
                "stopLossRate": 123,
                "takeProfitRate": 123,
                "trailingStopLoss": true,
                "orderId": 123,
                "socialTradeId": 123,
                "parentPositionId": 123,
                "investment": 123,
                "initialInvestment": 123,
                "fees": 123,
                "units": 123
            }

        """
        start_date = to_datetime(start_date)

        url = 'https://public-api.etoro.com/api/v1/trading/info/trade/history'
        params = {
            'minDate': start_date.isoformat()
        }
        response = requests.get(url, headers=self._headers(), params=params)
        return response.json()

    def portfolio_info(
        self,
        start_date: DateLike,
    ) -> list[dict[str, Any]]:
        """"
        Retrieves the portfolio information starting from the specified date.
        More info on the API endpoint here:
        https://api-portal.etoro.com/api-reference/
        trading--real/retrieve-comprehensive-portfolio-information-including-
        positions-orders-and-account-status

        Parameters:
        -----------
        start_date : DateLike
            The starting date for retrieving portfolio information.

        Returns:
        --------
        list[dict[str, Any]]
            A list of dictionaries containing the portfolio information with
            the following keys:
        """
        start_date = to_datetime(start_date)

        url = 'https://public-api.etoro.com/api/v1/trading/info/portfolio'
        params = {
            'minDate': start_date.isoformat()
        }
        response = requests.get(url, headers=self._headers(), params=params)
        return response.json()

    def convert_statement(
        self,
        path: Path | str,
    ) -> pd.DataFrame:
        """
        Converts the excel statement downloaded from the Etoro platform into a
        pandas DataFrame that the database can ingest.

        Parameters:
        -----------
        path : Path or str
            The file path to the excel statement.

        Returns:
        --------
        pd.DataFrame
            A pandas DataFrame containing the converted statement data with the
            following columns:
            - ts: The date and time of the transaction.
            - type: The type of transaction (e.g., open, close, deposit, etc.).
            - position_id: The ID of the position associated with the tx.
            - instrument_id: ID of the financial instrument involved in the tx.
            - units: The number of units/contracts involved in the transaction.
            - fee: The fee associated with the transaction (usd).
            - cashflow_usd: CF in USD for the transaction (includes fees).
            - notes: Any additional notes related to the transaction.
        """
        pf = pd.read_excel(
            path,
            sheet_name='Account Activity',
            na_values=['-'],
            parse_dates=['Date'],
            date_format='%d/%m/%Y %H:%M:%S',
            dtype={'Position ID': 'str'}
        )

        # ================================ FEES ===============================
        pf['dd'] = pf['Date'].apply(lambda x: x.date())
        fees = (
            pf.loc[
                pf['Type'].isin(['SDRT', 'Commission']),
                ['dd', 'Position ID', 'Amount']
            ]
            .groupby(['dd', 'Position ID'], as_index=False)['Amount']
            .sum()
            .rename(columns={'Amount': 'fee'})
        )
        pf = pf.merge(fees, on=['dd', 'Position ID'], how='left')
        pf['fee'] = pf['fee'].apply(lambda x: -x if x < 0 else x)

        # ========================= STYLE CORRECTIONS =========================
        # Only keep data we want
        pf = pf.rename(columns=STATEMENT_COLS_MAP)
        pf['type'] = pf['type'].map(STATEMENT_TYPES_MAP)
        pf = pf[list(STATEMENT_COLS_MAP.values())]
        pf = pf.dropna(subset=['type'])

        pf['cashflow_usd'] = np.where(
            pf['type'] == 'open',
            - pf['cashflow_usd'],
            pf['cashflow_usd']
        ) - pf['fee'].fillna(0)

        # Correct the holding change col
        pf['units'] = np.where(
            pf['type'] == 'close',
            - pf['units'],
            pf['units']
        )

        # Add notes where relevant (for splits)
        pf['notes'] = np.where(
            pf['type'] == 'split',
            pf['instrument_id'].str.split(' ').str[-1],
            None
        )

        # ======================= INSTRUMENT ID MAPPING =======================
        pf.loc[pf['type'] == 'deposit', 'instrument_id'] = pd.NA
        pf['instrument_id'] = (
            pf['instrument_id'].str.split('/').str[0].str.replace('.RTH', '')
        )

        mapper = dict()

        for id in pf['instrument_id'].dropna().unique():
            mapper[id] = self.search(
                    lookup=id,
                    field='internalSymbolFull',
                    return_fields=['instrumentId'],
                    strict=False,
                    ignore_internal=True
            )['instrumentId']
            time.sleep(API_SLEEP)

        ids = [v for v in mapper.values()]
        to_iid = get_iid_mapping(ids, source='ETORO')

        mapper = {k: to_iid.get(str(v)) for k, v in mapper.items()}

        pf['instrument_id'] = pf['instrument_id'].map(mapper)

        # ============================== SPLITS ===============================
        splits_window = pf.loc[pf['type'] == 'split']

        # This is slow, but not a lot of splits so I like the readability
        for _, row in splits_window.iterrows():
            # Get the holdings at the time of the split
            holdings = (
                pf.loc[
                    (pf['ts'] < row['ts'])
                    & (pf['position_id'] == row['position_id'])
                ]
                .groupby('instrument_id')['units']
                .cumsum()
                .iloc[0]
            )
            mutiplier = (
                float(row['notes'].split(':')[0]) /
                float(row['notes'].split(':')[1])
            )
            adjust = holdings * (mutiplier - 1)
            pf.at[row.name, 'units'] = adjust

        return pf

    def _headers(self):
        """Returns the headers for the request"""
        return {
            "x-api-key": self.keys['api'],
            "x-user-key": self.keys['user'],
            "x-request-id": str(uuid.uuid4())
        }


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    pass
