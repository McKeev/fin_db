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
import datetime as dt
import requests
import uuid
# Third Party Imports
# Local Imports

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------

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
        strict: bool = True
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
            fields.`
        strict : bool, default=True
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

        url = "https://public-api.etoro.com/api/v1/market-data/search"
        params = {
            field: lookup
        }

        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code == 200:
            # TODO Exclude 24_7 instruments
            data = response.json()
            if strict:
                # Find the exact match in the returned items list
                instrument = next(
                    (item for item in data['items']
                     if item[field] == lookup), None
                )
            else:
                # Return the first item from the search results
                instrument = next(
                    (item for item in data['items']), None
                )

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
        start_date: str | dt.datetime | dt.date,
    ) -> list[dict]:
        """"
        Retrieves the trade history starting from the specified date.
        More info on the API endpoint here:
        https://api-portal.etoro.com/api-reference/
        trading--real/list-trading-history

        Parameters:
        -----------
        start_date : str or datetime or date
            The starting date for retrieving trade history. Can be a string in
            ISO format (YYYY-MM-DD) or a datetime/date object.

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
        if isinstance(start_date, str):
            try:
                start_date = dt.datetime.fromisoformat(start_date)
            except ValueError:
                raise ValueError(
                    "start_date string must be in ISO format: YYYY-MM-DD"
                )
        elif isinstance(start_date, dt.datetime):
            start_date = start_date.date()

        url = 'https://public-api.etoro.com/api/v1/trading/info/trade/history'
        params = {
            'minDate': start_date.isoformat()
        }
        response = requests.get(url, headers=self._headers(), params=params)
        return response.json()

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
