import pandas as pd

# Read the CSV file and store relevant information in a DataFrame
df = pd.read_csv('data/ind_nifty100list.csv', usecols=['Company Name', 'Industry', 'Symbol'])

# Save the DataFrame to a CSV file
df.to_csv('NSE data/companies.csv', index=False)
