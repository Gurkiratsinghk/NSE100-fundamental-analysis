"""
Ingest pipeline — orchestrates a full end-to-end run.

Order of operations
-------------------
1. init_db()                      — ensure all tables exist
2. fetch_and_update_nse100()      — sync constituent list; mark removals
3. get_all_scrape_symbols()       — includes BOTH active and removed companies
4. run_scraper_for_symbols()      — scrape + persist Finology data for all
5. Log summary statistics

Why scrape removed companies?
------------------------------
When a company leaves the NSE100 index, its historical fundamentals remain
valuable for analysis, backtesting, and avoiding survivorship bias. Removal
only affects its constituent status — scraping continues uninterrupted.
"""

from loguru import logger

from data.db import init_db
from scrapers.nse100_list import fetch_and_update_nse100, get_all_scrape_symbols, get_active_symbols
from scrapers.finology import run_scraper_for_symbols


def run_full_ingest() -> None:
    """
    Execute the complete ingest pipeline.

    Safe to run repeatedly — existing historical rows are always preserved.
    Each run adds only new fiscal years; nothing is overwritten.
    """
    logger.info("=" * 60)
    logger.info("NSE100 FUNDAMENTALS — FULL INGEST STARTED")
    logger.info("=" * 60)

    # Step 1 — initialise database tables
    init_db()

    # Step 2 — sync the NSE100 constituent list
    logger.info("Step 1/3: Updating NSE100 constituent list...")
    fetch_and_update_nse100()

    # Step 3 — resolve scrape targets from DB
    # get_all_scrape_symbols() includes both active AND previously removed
    # companies so no historical coverage is lost after an index rebalance
    logger.info("Step 2/3: Resolving scrape targets from DB...")
    all_symbols    = get_all_scrape_symbols()
    active_symbols = get_active_symbols()
    removed_count  = len(all_symbols) - len(active_symbols)

    logger.info(
        f"  Active in index  : {len(active_symbols)}\n"
        f"  Previously removed (still tracked): {removed_count}\n"
        f"  Total to scrape  : {len(all_symbols)}"
    )

    if not all_symbols:
        logger.warning(
            "No symbols found in DB — the NSE100 list update may have failed. "
            "Aborting ingest."
        )
        return

    # Step 4 — scrape Finology for every symbol
    logger.info(f"Step 3/3: Scraping Finology for {len(all_symbols)} companies...")
    success, failure = run_scraper_for_symbols(all_symbols)

    # Summary
    logger.info("=" * 60)
    logger.info("INGEST COMPLETE")
    logger.info(f"  Total companies attempted : {len(all_symbols)}")
    logger.info(f"  Succeeded                 : {success}")
    logger.info(f"  Failed                    : {failure}")
    logger.info("=" * 60)