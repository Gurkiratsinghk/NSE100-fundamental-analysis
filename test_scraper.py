import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'nse_project'))
from scrapers.finology import scrape_company

symbol = "RELIANCE" # Assuming ID 1 is Reliance or something, or we can use any symbol like "TCS"
import sqlite3
conn = sqlite3.connect('nse_project/data/nse_fundamentals.db')
cursor = conn.cursor()
cursor.execute('SELECT symbol FROM companies WHERE id=1')
symbol = cursor.fetchone()[0]

data = scrape_company(symbol)
print(data.get('essentials'))
