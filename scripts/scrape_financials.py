# /scripts/scrape_financials.py

# Not working. Try with one company only.  

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Load company data
companies_df = pd.read_csv('data/companies.csv')

# Initialize a list to store financial data
financial_data = []

# Iterate over each company in the DataFrame
for index, row in companies_df.iterrows():
    company_name = row['Company Name']
    stock_symbol = row['Symbol']

    # Construct the URL to scrape data
    url = f"https://www.screener.in/company/{stock_symbol}/"

    try:
        # Fetch the page content
        response = requests.get(url)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract data from the "top-ratios" class
        top_ratios = soup.find('ul', id='top-ratios')
        market_cap = top_ratios.find('li', text="Market Cap").find_next('span', class_='number').string
        stock_pe = top_ratios.find('li', text="Stock P/E").find_next('span', class_='number').text
        roce = top_ratios.find('li', text="ROCE").find_next('span', class_='number').text
        book_value = top_ratios.find('li', text="Book Value").find_next('span', class_='number').text
        roe = top_ratios.find('li', text="ROE").find_next('span', class_='number').text
        dividend_yield = top_ratios.find('li', text="Dividend Yield").find_next('span', class_='number').text

        # Extract data from the Profit & Loss table
        pl_section = soup.find('section', id='profit-loss')
        compounded_sales_growth = pl_section.find('table', class_='ranges-table').find_all('td', text="Compounded Sales Growth")
        compounded_profit_growth = pl_section.find('table', class_='ranges-table').find_all('td', text="Compounded Profit Growth")
        stock_price_cagr = pl_section.find('table', class_='ranges-table').find_all('td', text="Stock Price CAGR")
        roe_years = pl_section.find('table', class_='ranges-table').find_all('td', text="Return on Equity")

        # Extract other financial data from the balance sheet, cash flow, etc.
        balance_sheet_section = soup.find('section', id='balance-sheet')
        equity_capital = balance_sheet_section.find(text="Equity Capital").find_next('td').text
        reserves = balance_sheet_section.find(text="Reserves").find_next('td').text

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
            'Equity Capital': equity_capital,
            'Reserves': reserves,
            # Add other financial metrics similarly...
        })

    except Exception as e:
        print(f"Error scraping data for {company_name} ({stock_symbol}): {e}")

# Convert the list to a DataFrame
financials_df = pd.DataFrame(financial_data)

# Save the financial data to a CSV file
financials_df.to_csv('data/financials.csv', index=False)
