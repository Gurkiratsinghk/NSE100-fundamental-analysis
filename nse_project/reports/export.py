"""
Export utilities — converts database tables to CSV for inspection.

Usage
-----
from reports.export import export_table, export_fundamentals_wide

export_table("yearly_financials", "reports/yearly_financials.csv")
export_fundamentals_wide("reports/fundamentals_wide.csv")
"""

from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import text

from data.db import engine


# ---------------------------------------------------------------------------
# Generic table exporter
# ---------------------------------------------------------------------------

def export_table(table_name: str, output_path: str | None = None) -> None:
    """
    Dump an entire database table to CSV, joined with company symbol and name
    where a company_id foreign key exists.

    Parameters
    ----------
    table_name  : exact name of the SQLite table (e.g. "yearly_financials")
    output_path : destination CSV path; defaults to reports/<table_name>.csv
    """
    if output_path is None:
        output_path = f"reports/{table_name}.csv"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Detect whether the table has a company_id column
    with engine.connect() as conn:
        pragma_result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in pragma_result]

    if "company_id" in columns:
        query = f"""
            SELECT c.symbol, c.company_name, t.*
            FROM {table_name} t
            JOIN companies c ON c.id = t.company_id
            ORDER BY c.symbol
        """
    else:
        query = f"SELECT * FROM {table_name}"

    try:
        df = pd.read_sql(query, con=engine)
        # Drop the redundant company_id column when we already have symbol
        if "company_id" in df.columns and "symbol" in df.columns:
            df.drop(columns=["company_id"], inplace=True)

        df.to_csv(output_path, index=False)
        logger.success(f"Exported '{table_name}' → {output_path}  ({len(df)} rows)")
    except Exception as exc:
        logger.error(f"Failed to export '{table_name}': {exc}")


# ---------------------------------------------------------------------------
# Wide-format fundamentals export
# ---------------------------------------------------------------------------

def export_fundamentals_wide(output_path: str = "reports/fundamentals_wide.csv") -> None:
    """
    Pivot yearly_financials from EAV (long) format into a wide table where
    each unique (source_table, metric_name) combination becomes a column.

    Resulting columns:
        symbol | company_name | fiscal_year | pl_revenue | pl_net_profit | bs_total_assets | ...

    This is the most analysis-friendly format.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    query = """
        SELECT
            c.symbol,
            c.company_name,
            yf.fiscal_year,
            yf.source_table,
            yf.metric_name,
            yf.value_num,
            yf.value_text
        FROM yearly_financials yf
        JOIN companies c ON c.id = yf.company_id
        ORDER BY c.symbol, yf.fiscal_year, yf.source_table, yf.metric_name
    """

    try:
        df = pd.read_sql(query, con=engine)

        if df.empty:
            logger.warning("yearly_financials is empty — nothing to export.")
            return

        # Build a combined column key: e.g. "pl_revenue", "bs_total_assets"
        source_abbr = {"profit_loss": "pl", "balance_sheet": "bs", "cash_flow": "cf"}
        df["col_key"] = (
            df["source_table"].map(source_abbr).fillna(df["source_table"])
            + "_"
            + df["metric_name"]
        )

        # Prefer numeric; fall back to text
        df["value"] = df["value_num"].combine_first(df["value_text"].apply(
            lambda x: None if pd.isna(x) else x
        ))

        pivot = df.pivot_table(
            index   = ["symbol", "company_name", "fiscal_year"],
            columns = "col_key",
            values  = "value",
            aggfunc = "first",
        ).reset_index()

        pivot.columns.name = None
        pivot.to_csv(output_path, index=False)
        logger.success(
            f"Wide fundamentals export → {output_path}  "
            f"({len(pivot)} rows × {len(pivot.columns)} columns)"
        )

    except Exception as exc:
        logger.error(f"Failed to export wide fundamentals: {exc}")


# ---------------------------------------------------------------------------
# Essentials exporter
# ---------------------------------------------------------------------------

def export_essentials(output_path: str = "reports/company_essentials.csv") -> None:
    """
    Export company_essentials in wide format:
        symbol | company_name | metric_1 | metric_2 | ...
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    query = """
        SELECT
            c.symbol,
            c.company_name,
            e.metric_name,
            e.value_num,
            e.value_text,
            e.scraped_at
        FROM company_essentials e
        JOIN companies c ON c.id = e.company_id
        ORDER BY c.symbol, e.metric_name
    """

    try:
        df = pd.read_sql(query, con=engine)

        if df.empty:
            logger.warning("company_essentials is empty — nothing to export.")
            return

        df["value"] = df["value_num"].combine_first(df["value_text"].apply(
            lambda x: None if pd.isna(x) else x
        ))

        pivot = df.pivot_table(
            index   = ["symbol", "company_name"],
            columns = "metric_name",
            values  = "value",
            aggfunc = "first",
        ).reset_index()

        pivot.columns.name = None
        pivot.to_csv(output_path, index=False)
        logger.success(
            f"Essentials export → {output_path}  "
            f"({len(pivot)} companies × {len(pivot.columns)} columns)"
        )

    except Exception as exc:
        logger.error(f"Failed to export essentials: {exc}")
