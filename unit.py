import requests
import requests
import pandas as pd
import json
# from IPython.display import display
from bs4 import BeautifulSoup
import pandas as pd
import re


company_symbol = 'ABB'
finology_url = f'https://ticker.finology.in/company/{company_symbol}'

print(f"Company Symbol: {company_symbol}")
print(f"Finology URL: {finology_url}")


# 1. Define the NSE API URL for the NIFTY 100 index
url = 'https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20100'

extracted_data = []

try:
    # 2. Make an HTTP GET request to the NSE API URL, including a 'User-Agent' header
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    # 3. Check if the request was successful
    response.raise_for_status() # Raise an exception for HTTP errors

    # 4. Parse the JSON response received from the API
    json_data = response.json()

    # 5. Iterate through the 'data' array in the JSON response
    if 'data' in json_data:
        for item in json_data['data']:
            # 6. For each item in 'data', check if it contains a 'meta' object and extract info
            if 'meta' in item:
                symbol = item['meta'].get('symbol')
                company_name = item['meta'].get('companyName')
                industry = item['meta'].get('industry')

                # Ensure at least one piece of information is present before adding
                if symbol or company_name or industry:
                    extracted_data.append({
                        'Symbol': symbol,
                        'CompanyName': company_name,
                        'Industry': industry
                    })

    # 8. Convert the list of dictionaries into a Pandas DataFrame named df_nse_data
    if extracted_data:
        df_nse_data = pd.DataFrame(extracted_data)
        print("Successfully extracted basic company information for NIFTY 100 constituents.")
        # 9. Print the head of the df_nse_data DataFrame
        print("\nHead of extracted NSE Data:")
        # display(df_nse_data.head())
    else:
        print("No relevant company data found in the NSE API response.")

except requests.exceptions.RequestException as e:
    print(f"An error occurred during the API call: {e}")
    print(f"Response content (if available): {response.text[:500]}")
except json.JSONDecodeError:
    print("The response could not be decoded as JSON.")
    print(f"Response content: {response.text[:500]}")


# Ensure finology_url is defined from previous steps
# finology_url = 'https://ticker.finology.in/company/ABB' # Uncomment if running standalone

response_abb = requests.get(finology_url)

if response_abb.status_code == 200:
    print(f"Successfully fetched the webpage content from {finology_url}.")
else:
    print(f"Failed to fetch the webpage from {finology_url}. Status code: {response_abb.status_code}")


soup_abb = BeautifulSoup(response_abb.text, 'html.parser')
print("HTML content successfully parsed into a BeautifulSoup object for ABB.")

tables_abb = soup_abb.find_all('table')
print(f"Found {len(tables_abb)} tables on the page for ABB.")

if tables_abb:
    for i, table in enumerate(tables_abb):
        print(f"\nTable {i+1}:")
        # Print the first few rows of each table to get an idea of its content
        if i == 3:
          rows = table.find_all(['thead', 'tr'])
          for j, row in enumerate(rows):
            cols = row.find_all(['th', 'td'])
            print([col.get_text(strip=True) for col in cols])
        else:
          rows = table.find_all('tr')
          for j, row in enumerate(rows):
              
                cols = row.find_all(['th', 'td'])
                print([col.get_text(strip=True) for col in cols])
              
else:
    print("No tables found on the page for ABB.")


# Reusing the parse_table_to_dataframe function from previous steps
def parse_table_to_dataframe(table_soup, known_year_headers=None):
    rows = table_soup.find_all('tr')
    if not rows:
        return pd.DataFrame()

    # Extract headers from the first row, including both th and td
    header_cells = rows[0].find_all(['th', 'td'])
    raw_headers = [cell.get_text(strip=True) for cell in header_cells]

    # Determine headers based on content and known_year_headers
    # This condition matches the Balance Sheet pattern: ['Category', '', '', ..., '']
    if known_year_headers and len(raw_headers) > 1 and all(h == '' for h in raw_headers[1:]):
        final_headers = [raw_headers[0]] + known_year_headers
        start_row_index = 1 # Skip the original header row as it's now reconstructed
    else:
        # Existing header cleaning logic for tables with explicit headers (like income statement)
        cleaned_headers = []
        for i, h in enumerate(raw_headers):
            if h == '':
                cleaned_headers.append(f'Column_{i}' if i > 0 else 'Particulars')
            else:
                cleaned_headers.append(h)

        final_headers = []
        seen_headers = {}
        for h in cleaned_headers:
            if h in seen_headers:
                seen_headers[h] += 1
                final_headers.append(f'{h}_{seen_headers[h]}')
            else:
                seen_headers[h] = 0
                final_headers.append(h)
        start_row_index = 1 # Data typically starts from the second row

    data = []
    for row in rows[start_row_index:]:
        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]

        # Ensure the row has the same number of columns as final_headers.
        # If a row has more columns (like Table 5), truncate it.
        if len(cols) > len(final_headers):
            data.append(cols[:len(final_headers)])
        elif len(cols) == len(final_headers):
            data.append(cols)
        # Rows with fewer columns are implicitly skipped.

    if not data:
        return pd.DataFrame(columns=final_headers)

    df = pd.DataFrame(data, columns=final_headers)

    # Convert numeric columns, assuming first column is descriptive
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col].str.replace(',', '').replace('-', '0'), errors='coerce')

    return df

# Extract Table 3 (Annual Income Statement) for ABB FIRST to get year headers
annual_income_statement_table_abb = tables_abb[2]
annual_income_statement_df_abb = parse_table_to_dataframe(annual_income_statement_table_abb)
print("\nAnnual Income Statement (Table 3) for ABB:")
print(annual_income_statement_df_abb.head())

# Extract year headers from the Annual Income Statement for reuse
# Assuming 'PARTICULARS' is always the first column
financial_year_headers = annual_income_statement_df_abb.columns[1:].tolist()

# Extract Table 4 (Balance Sheet) for ABB using the extracted year headers
balance_sheet_table_abb = tables_abb[3]
balance_sheet_df_abb = parse_table_to_dataframe(balance_sheet_table_abb, known_year_headers=financial_year_headers)

# Insert header rows for balance sheet structure
# Row 1: "Particulars" in column 1, with years as headers
# Row 2: "Equity and Liabilities" in column 1, with NaN in other columns
particulars_row = pd.DataFrame([['Particulars'] + financial_year_headers], columns=balance_sheet_df_abb.columns)
equity_liabilities_row = pd.DataFrame([['Equity and Liabilities'] + [float('nan')] * len(financial_year_headers)], columns=balance_sheet_df_abb.columns)

# Combine: header rows + original data
balance_sheet_df_abb = pd.concat([particulars_row, equity_liabilities_row, balance_sheet_df_abb], ignore_index=True)

print("\nBalance Sheet (Table 4) for ABB:")
print(balance_sheet_df_abb.head())

# Extract Table 5 (Cash Flow Statement) for ABB
# The function should correctly use Table 5's own headers as they are explicit.
cash_flow_statement_table_abb = tables_abb[4]
cash_flow_statement_df_abb = parse_table_to_dataframe(cash_flow_statement_table_abb, known_year_headers=financial_year_headers)
print("\nCash Flow Statement (Table 5) for ABB:")
print(cash_flow_statement_df_abb.head())


# Re-initialize company_essentials for ABB
company_essentials_abb = {}
companyessentials_div_abb = soup_abb.find('div', id='companyessentials')

if companyessentials_div_abb:
    # Look for container divs within companyessentials_div that hold key-value pairs
    # These often have column classes like 'col-6', 'col-md-4', or margin-bottom classes like 'mb-2'
    metric_containers_abb = companyessentials_div_abb.find_all('div', class_=lambda x: x and ('col-' in x or 'mb-' in x))

    for container_div in metric_containers_abb:
        # Based on the provided HTML structure, labels are typically in <small> and values in <p>
        label_tag = container_div.find('small')
        value_tag = container_div.find('p')

        if label_tag and value_tag:
            label = label_tag.get_text(strip=True)
            value = value_tag.get_text(strip=True)

            # Filter out entries where the label is purely numeric and the value is 'Cr.' (irrelevant units)
            if label.replace('.', '', 1).isdigit() and value == 'Cr.':
                continue

            # Ensure the label is not purely numeric (e.g., year numbers, dates) and the value is not empty
            if not label.replace('.', '', 1).isdigit() and value:
                # Further clean value: remove leading/trailing whitespace, newlines, and unnecessary characters
                value = value.replace('\r', '').replace('\n', '').strip()
                company_essentials_abb[label] = value
else:
    print("Element with id='companyessentials' not found for ABB.")

print("Extracted Company Essentials for ABB:")
if company_essentials_abb:
    for key, value in company_essentials_abb.items():
        print(f"- {key}: {value}")
else:
    print("No Company Essentials found using specified <small>/<p> patterns within 'companyessentials' block for ABB.")

promoter_shareholding_table_abb = tables_abb[5]
promoter_shareholding_df_abb = parse_table_to_dataframe(promoter_shareholding_table_abb)
print("\nPromoter Shareholding (Table 6) for ABB:")
print(promoter_shareholding_df_abb.head())

investor_shareholding_table_abb = tables_abb[6]
investor_shareholding_df_abb = parse_table_to_dataframe(investor_shareholding_table_abb)
print("\nInvestor Shareholding (Table 7) for ABB:")
print(investor_shareholding_df_abb.head())    

print("\n--- Annual Income Statement (ABB) ---")
print(annual_income_statement_df_abb.to_markdown(index=False))

print("\n--- Balance Sheet (ABB) ---")
print(balance_sheet_df_abb.to_markdown(index=False))

print("\n--- Cash Flow Statement (ABB) ---")
print(cash_flow_statement_df_abb.to_markdown(index=False))

print("\n--- Promoter Shareholding (ABB) ---")
print(promoter_shareholding_df_abb.to_markdown(index=False))

print("\n--- Investor Shareholding (ABB) ---")
print(investor_shareholding_df_abb.to_markdown(index=False))

print("\n--- Company Essentials (ABB) ---")
if company_essentials_abb:
    for key, value in company_essentials_abb.items():
        print(f"- {key}: {value}")
else:
    print("No Company Essentials available for ABB.")