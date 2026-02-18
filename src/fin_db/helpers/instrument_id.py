"""
File Name: instrument_id.py
Author: Cedric McKeever
Date: 2026-02-18
Description:
Creates the instrument_id used in the database
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
import re

# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------

ASSET_CLASSES = {
    "equity": "EQU",
    "etf": "ETF",
    "index": "IND",
    "crypto": "CRY",
    "currency": "CUR",
    "commodity": "COM",
}

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


def instrument_id(asset_class: str, code: str, hash_on: str) -> str:
    """
    Constructs a deterministic instrument id.
    Length:          3            4     13   = 20 chars total
    Format: {ASSET_CLASS_CODE}_{CODE}_{HASH}
    """

    # Validate and normalize asset_class
    normalized_asset_class = asset_class.strip().lower()
    asset_code = ASSET_CLASSES.get(normalized_asset_class)
    if not asset_code:
        raise ValueError(f"Unsupported asset class: {asset_class}")
    # Validate and normalize code
    if not code:
        raise ValueError("Code cannot be empty")
    if (len(code) > 4) or (code.isalnum() is False):
        raise ValueError("Code must be <= 4 alphanumerical characters")
    code = code.upper().ljust(4, "X")
    # Validate hash_on based on asset class
    match normalized_asset_class:
        case "equity":
            if _valid_isin(hash_on):
                hash_val = hash_on.upper().ljust(13, "X")
            else:
                raise ValueError(
                    f"Invalid ISIN for {normalized_asset_class}: {hash_on}"
                )
        case _:
            raise NotImplementedError(
                "Hash creation not implemented for this asset class."
            )

    return f"{asset_code}{code}{hash_val}"


def _valid_isin(isin: str) -> bool:
    """Validate ISIN via format + Luhn checksum."""
    if not _ISIN_RE.fullmatch(isin):
        return False

    expanded = []
    for char in isin:
        if char.isdigit():
            expanded.append(char)
        else:
            expanded.append(str(ord(char) - ord("A") + 10))

    digits = "".join(expanded)

    total = 0
    double = False
    for digit in reversed(digits):
        num = int(digit)
        if double:
            num *= 2
            if num > 9:
                num -= 9
        total += num
        double = not double

    return total % 10 == 0


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    pass
