import sqlite3
import pandas as pd

conn = sqlite3.connect('nse_project/data/nse_fundamentals.db')
df = pd.read_sql('SELECT company_id, metric_name, value_num, value_text FROM company_essentials WHERE metric_name LIKE "%_54" OR metric_name LIKE "%_72%" OR metric_name GLOB "*[0-9]*"', conn)
print(df.head(50))
