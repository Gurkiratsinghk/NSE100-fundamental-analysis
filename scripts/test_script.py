# python /scripts/scrape_financials.py

import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# Manually define the single company you want to test with
test_company = {
    'Company Name': 'Amara Raja Energy & Mobility Ltd',
    'Symbol': 'ARE&M'
}

# Initialize a list to store financial data
financial_data = []

# Extract company information
company_name = test_company['Company Name']
stock_symbol = test_company['Symbol']

# Construct the URL to scrape data
url = f"https://www.screener.in/company/{stock_symbol}/"

try:
    # Fetch the page content
    response = requests.get(url)
    response.raise_for_status()

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    def get_text_or_none(element):
        """Helper function to safely get text or return None."""
        return element.get_text(strip=True) if element else None

    # Extract data from the "top-ratios" section
    top_ratios = soup.find('ul', id='top-ratios')

    # Use regex to match the key indicators
    market_cap = get_text_or_none(top_ratios.find('span', string=re.compile(r"\s*Market Cap\s*", re.IGNORECASE)).find_next('span', class_='number'))
    stock_pe = get_text_or_none(top_ratios.find('span', string=re.compile(r"\s*Stock P/E\s*", re.IGNORECASE)).find_next('span', class_='number'))
    roce = get_text_or_none(top_ratios.find('span', string=re.compile(r"\s*ROCE\s*", re.IGNORECASE)).find_next('span', class_='number'))
    book_value = get_text_or_none(top_ratios.find('span', string=re.compile(r"\s*Book Value\s*", re.IGNORECASE)).find_next('span', class_='number'))
    roe = get_text_or_none(top_ratios.find('span', string=re.compile(r"\s*ROE\s*", re.IGNORECASE)).find_next('span', class_='number'))
    dividend_yield = get_text_or_none(top_ratios.find('span', string=re.compile(r"\s*Dividend Yield\s*", re.IGNORECASE)).find_next('span', class_='number'))

    # Extract data from the Profit & Loss section
    pl_section = soup.find('section', id='profit-loss')
    # Extract data fron the Compounded Sales Growth section
    compounded_sales_growth = pl_section.find_all('table' , class_='ranges-table')[0]
    compounded_sales_growth_10 = get_text_or_none(compounded_sales_growth.find_all('td')[1])
    compounded_sales_growth_5 = get_text_or_none(compounded_sales_growth.find_all('td')[3])
    compounded_sales_growth_3 = get_text_or_none(compounded_sales_growth.find_all('td')[5])
    compounded_sales_growth_last = get_text_or_none(compounded_sales_growth.find_all('td')[7])

    # Extract data from the Balance Sheet section
    balance_sheet_section = soup.find('section', id='balance-sheet')
    equity_capital = get_text_or_none(balance_sheet_section.find(string=re.compile(r"\s*Equity Capital\s*", re.IGNORECASE)).find_next('td'))
    reserves = get_text_or_none(balance_sheet_section.find(string=re.compile(r"\s*Reserves\s*", re.IGNORECASE)).find_next('td'))
    borrowings = get_text_or_none(balance_sheet_section.find(string=re.compile(r"\s*Borrowings\s*", re.IGNORECASE)).find_next('td'))

    # Add data to the list
    financial_data.append({
        'Company Name': company_name,
        'Stock Symbol': stock_symbol,
        'Market Cap': market_cap,
        'Stock P/E': stock_pe,
        'ROCE': roce,
        'Book Value': book_value,
        'ROE': roe,
        'Dividend Yield': dividend_yield,
        'Compounded Sales Growth 10Y': compounded_sales_growth_10, # Misscraping the data
        'Compounded Sales Growth 5Y': compounded_sales_growth_5, # Misscraping the data
        'Compounded Sales Growth 3Y': compounded_sales_growth_3, # Misscraping the data
        'Compounded Sales Growth Last Y': compounded_sales_growth_last, # Misscraping the data
        'Equity Capital': equity_capital, # 2013 data scraped
        'Reserves': reserves, # 2013 data scraped
        'Borrowings': borrowings, # 2013 data scraped
        
        # Add additional financial metrics similarly...
    })

finally:
    None

# except Exception as e:
    # print(f"Error scraping data for {company_name} ({stock_symbol}): {e}")

# Convert the list to a DataFrame
financials_df = pd.DataFrame(financial_data)

# Save the financial data to a CSV file
financials_df.to_csv('data/financials_test.csv', index=False)

print(financials_df)
