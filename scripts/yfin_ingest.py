"""
File Name: yfin_daily.py
Author: Cedric McKeever
Date: 2026-03-17
Description:
Script for daily ingesting for `observations` table.
"""

# ----------------------------------------------------------------------------
# ============================== IMPORTS =====================================
# ----------------------------------------------------------------------------
# First Party Imports
import datetime as dt
import os
from pathlib import Path
from typing import Literal
# Third Party Imports
from dotenv import load_dotenv
import pandas as pd
# Local Imports
import fin_db as fdb


# ----------------------------------------------------------------------------
# ============================= CONSTANTS ====================================
# ----------------------------------------------------------------------------

_FIN_DB_DIR = Path(__file__).parent.parent
_LOG_FILE = _FIN_DB_DIR / 'logs' / 'yahoo_daily_ingest.log'
_BATCH_SIZE = 5
_MAX_ATTEMPTS = 5
load_dotenv(_FIN_DB_DIR / "scripts/.env")
fdb.setup_telebot(
    token=os.getenv('TELEGRAM_BOT_TOKEN'),
    chat_id=os.getenv('TELEGRAM_CHAT_ID'),
)
logger = fdb.setup_logger(
    'yahoo_daily_ingest',
    log_file=_LOG_FILE,
    telegram_critical=True,
)


# ----------------------------------------------------------------------------
# ============================= FUNCTIONS ====================================
# ----------------------------------------------------------------------------


def etl(
    fields: list[str],
    tickers: list[str],
    sdate: str,
    edate: str,
    transform: Literal['normal', 'currency'] = 'normal',
):
    """ETL function for Yahoo Finance data."""

    puller = fdb.providers.YFinPuller(
        tickers=tickers,
        sdate=sdate,
        edate=edate,
        batch_size=_BATCH_SIZE,
        max_attempts=_MAX_ATTEMPTS,
    )

    df, failed = puller.histpull(
        fields=fields,
        return_failed=True
    )

    if df.empty:
        logger.error("No data pulled for all tickers in batch")
        return

    # Need to change the tickers back to internal `instrument_id`s
    needed_iids = list(set(df['identifier'].unique()) | set(failed))
    iid_mapping = fdb.queries.get_iid_mapping(
        tickers=needed_iids,
        source='YAHOO'
    )
    df['identifier'] = df['identifier'].map(iid_mapping)
    df = df.rename(columns={'identifier': 'instrument_id'})

    if transform == 'currency':
        # We pull the rate in indirect form for more precision,
        # but we to store it in direct form in the DB
        df['value'] = 1 / df['value']
        df['value'] = df['value'] / 0.00001  # Store as pipette

        # Create USD observations for each date in the df
        dates = df['date'].unique()
        usd_df = pd.DataFrame({
            'instrument_id': 'CURUSDXUSDXXXXXXXXXX',
            'field': 'close',
            'date': dates,
            'value': 100_000,  # 1 pipette in USD
            'source': 'system',
        })
        df = pd.concat([df, usd_df], ignore_index=True)

    # Write to DB
    fdb.queries.ingest_observations(
        df=df,
        commit=True
    )

    if failed:
        fail_pct = len(failed) / len(tickers) * 100
        if fail_pct < 10:
            logger.error(
                f'Failed to pull data for {len(failed)} of {len(tickers)} '
                f'tickers ({fail_pct:.2f}%)'
            )
        else:
            logger.critical(
                f'Failed to pull data for {len(failed)} of {len(tickers)} '
                f'tickers ({fail_pct:.2f}%)'
            )
        # Construct a DataFrame for the failed tickers (with fields)
        failed_df = pd.DataFrame(
            {
                'instrument_id': iid_mapping.get(ticker),
                'field': field,
                'source': 'YAHOO',
                'error_message': error,
            }
            for ticker, error in failed.items()
            for field in fields
        )

        fdb.queries.log_failed_ingest(
                df=failed_df,
                commit=True
        )


def main():
    update_dict = fdb.queries.to_update(frequency='daily', source='YAHOO')
    today = dt.date.today()
    sdate = today - dt.timedelta(days=30)

    for (asset_class, fields), tickers in update_dict.items():
        if asset_class == 'currency':
            etl(
                fields=list(fields),
                tickers=tickers,
                sdate=str(sdate),
                edate=str(today),
                transform='currency',
            )
            # Refresh materialized view for currency pairs
            conn = fdb.session.db_conn()
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW units_ts;")
                conn.commit()
                logger.info("Refreshed materialized view: units_ts")
        else:
            etl(
                fields=list(fields),
                tickers=tickers,
                sdate=str(sdate),
                edate=str(today),
                transform='normal',
            )

    # Refresh materialized view for time series data
    conn = fdb.session.db_conn()
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW time_series_usd;")
        conn.commit()
        logger.info("Refreshed materialized view: time_series_usd")

    # Check for any instruments that have not been updated in the last 5 days
    no_updates = fdb.queries.check_updates(
        cutoff_date=str(today - dt.timedelta(days=5))
    )
    if no_updates:
        no_updates = pd.DataFrame(no_updates)
        no_updates = no_updates.groupby(
            ['instrument_id', 'name', 'last_update']
        )['field'].apply(tuple).reset_index()

        formatted_no_updates = "\n".join(
            f"- {name} ({iid}), "
            f"field(s): {', '.join(field for field in fields)}. "
            f"Last updated {last_update} "
            f"({(today - last_update).days} "
            "days ago)"
            for iid, name, last_update, fields
            in no_updates.itertuples(index=False)
        )
        fdb.get_telebot().send_msg(
            "WARNING:\n"
            f"Found {len(no_updates)} instruments-fields that have not been "
            "updated in the last 5 days.\n\n"
            f"{formatted_no_updates}"
        )
    # Clean logs
    fdb.helpers.clear_old_logs(_LOG_FILE, days=30)


# ----------------------------------------------------------------------------
# =============================== MAIN =======================================
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        fdb.open_session(
            user='fin_db_app',
            host='minicomp',
        )
        main()
        fdb.get_telebot().send_msg(
            "Yahoo daily ingest completed successfully."
        )
    except Exception as e:
        # Should not be possible for an exception to be raised without being
        # caught in the main(). This is just a precaution.
        logger.critical(f"Exception occurred during main execution:\n\n {e}")
