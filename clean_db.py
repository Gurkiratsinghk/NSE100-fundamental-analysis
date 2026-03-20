import sqlite3
import pandas as pd
import sys
import os

# Create a function equivalent to what `_parse_value` expects to see what to delete
def is_numeric_label(label: str) -> bool:
    try:
        # replicate _clean_numeric_string
        cleaned = label.strip().replace('\xa0', ' ').replace(',', '').replace('\u20b9', '').replace('Rs', '').replace('Cr.', '').replace('Cr', '').replace('%', '').strip()
        if cleaned in ("", "-", "--", "N/A", "NA", "n/a"): return False
        float(cleaned)
        return True
    except ValueError:
        return False

# But wait, metric_name in the DB is snake_cased. e.g. "126869_54" or "121361_72cr"
# Since valid metric_names never have numbers (except maybe '52_week_high' but that's not in the essentials table), 
# actually let's just delete rows where the metric_name has ANY digits in it!
# Wait, let's verify if there are any valid metrics with digits.
conn = sqlite3.connect('nse_project/data/nse_fundamentals.db')
c = conn.cursor()

c.execute('SELECT DISTINCT metric_name FROM company_essentials')
all_metrics = [r[0] for r in c.fetchall()]

valid_metrics = []
delete_metrics = []

for m in all_metrics:
    # A valid metric string from finology companyessentials
    # e.g. "market_cap", "p_e", "book_value_ttm"
    # if it has digits, it's probably junk like "121361_72cr"
    if any(char.isdigit() for char in m):
        delete_metrics.append(m)
    else:
        valid_metrics.append(m)

print(f"Valid metrics without digits: {valid_metrics}")
print(f"Junk metrics to delete: {len(delete_metrics)}")

# Perform deletion
deleted = 0
for bad_m in delete_metrics:
    c.execute('DELETE FROM company_essentials WHERE metric_name = ?', (bad_m,))
    deleted += c.rowcount

conn.commit()
print(f"Deleted {deleted} rows from company_essentials.")
