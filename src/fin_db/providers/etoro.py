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
    ):
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
            data = response.json()
            # Find the exact match in the returned items list
            instrument = next(
                (item for item in data['items'] if item[field] == lookup), None
            )

            if instrument:
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
