from playwright.async_api import async_playwright
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
import time
import re
from pathlib import Path
import sqlite3
import json

class FinancialScraperPlaywright:
    def __init__(self):
        """Initialize the scraper with necessary configurations"""
        self.base_url = "https://www.screener.in/company/"
        self.setup_logging()
        self.setup_data_directory()
        self.setup_database()
        
    def setup_data_directory(self):
        """Setup directory for storing scraped data"""
        self.data_dir = Path('../scraper_v1.0_data')
        self.data_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            filename=f'scraping_log_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def setup_database(self):
        """Setup SQLite database and create necessary tables"""
        self.db_path = self.data_dir / 'financial_data.db'
        
        with sqlite3.connect(str(self.db_path)) as conn:
            c = conn.cursor()
            
            # Create tables for each type of data
            c.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    ticker TEXT PRIMARY KEY,
                    last_updated TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS financial_data (
                    ticker TEXT,
                    data_type TEXT,
                    date TEXT,
                    metric TEXT,
                    value REAL,
                    PRIMARY KEY (ticker, data_type, date, metric)
                )
            ''')
            
            conn.commit()

    def save_to_database(self, data: Dict[str, pd.DataFrame], ticker: str):
        """Save financial data to SQLite database"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Update companies table
                conn.execute(
                    "INSERT OR REPLACE INTO companies (ticker, last_updated) VALUES (?, ?)",
                    (ticker, datetime.now().isoformat())
                )
                
                # Save each dataframe to financial_data table
                for data_type, df in data.items():
                    if isinstance(df, pd.DataFrame):
                        # Reset index if it's not already a column
                        if isinstance(df.index, pd.Index):
                            df = df.reset_index()
                        
                        for _, row in df.iterrows():
                            metric = row.iloc[0]  # First column is metric name
                            for date, value in row.iloc[1:].items():
                                if pd.notnull(value):
                                    conn.execute('''
                                        INSERT OR REPLACE INTO financial_data 
                                        (ticker, data_type, date, metric, value)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (ticker, data_type, str(date), str(metric), float(value)))
                
                conn.commit()
                logging.info(f"Successfully saved {ticker} data to database")
                
        except Exception as e:
            logging.error(f"Error saving to database: {e}")
            raise

    def clean_number(self, value: str) -> Optional[float]:
        """Clean and convert string numbers to float"""
        try:
            value = str(value)
            value = value.replace('₹', '').replace('Cr.', '').replace('%', '').replace(',', '').strip()
            return float(value) if value and value != '-' else None
        except (ValueError, AttributeError):
            logging.warning(f"Could not convert value: {value}")
            return None

    async def expand_sections(self, page):
        """Click on all '+' buttons to expand sections"""
        try:
            # Wait for the page to load
            await page.wait_for_load_state('networkidle')
            
            # Find and click all '+' buttons
            buttons = await page.query_selector_all('button.button-plain:has(span.blue-icon)')
            for button in buttons:
                try:
                    # Check if the button contains the '+' symbol
                    span_text = await button.query_selector('span.blue-icon')
                    if span_text:
                        await button.click()
                        # Wait for any potential updates
                        await page.wait_for_timeout(500)
                except Exception as e:
                    logging.warning(f"Error clicking button: {e}")
                    continue
            
            # Wait for any final updates
            await page.wait_for_timeout(1000)
            
        except Exception as e:
            logging.error(f"Error expanding sections: {e}")
            raise

    async def extract_table_data(self, page, section_id: str) -> pd.DataFrame:
        """Extract data from a specific section using Playwright selectors"""
        try:
            # Wait for the section to be visible
            section = await page.wait_for_selector(f'section#{section_id}')
            if not section:
                raise ValueError(f"{section_id} section not found")
            
            # Extract headers
            headers = ['Metric']
            header_elements = await page.query_selector_all(f'section#{section_id} table.data-table th')
            for header in header_elements[1:]:  # Skip first header (empty)
                header_text = await header.inner_text()
                headers.append(header_text.strip())
            
            # Extract rows
            rows = []
            row_elements = await page.query_selector_all(f'section#{section_id} table.data-table tbody tr')
            
            for row_element in row_elements:
                row = []
                # Get metric name
                metric_element = await row_element.query_selector('td.text') or await row_element.query_selector('td:first-child')
                metric_name = await metric_element.inner_text()
                metric_name = re.sub(r'\s*[-+]\s*$', '', metric_name.strip())
                row.append(metric_name)
                
                # Get values for each year
                value_elements = await row_element.query_selector_all('td:not(:first-child)')
                for value_element in value_elements:
                    value_text = await value_element.inner_text()
                    value = self.clean_number(value_text.strip())
                    row.append(value)
                
                rows.append(row)
                
            # Create DataFrame
            df = pd.DataFrame(rows, columns=headers)
            df.set_index('Metric', inplace=True)
            return df
            
        except Exception as e:
            logging.error(f"Error extracting {section_id} data: {e}")
            return pd.DataFrame()

    async def extract_growth_metrics(self, page) -> pd.DataFrame:
        """Extract growth metrics tables using Playwright selectors"""
        try:
            growth_data = {}
            tables = await page.query_selector_all('table.ranges-table')
            
            for table in tables:
                category_element = await table.query_selector('th')
                category = await category_element.inner_text()
                category = category.strip()
                growth_data[category] = {}
                
                rows = await table.query_selector_all('tr:not(:first-child)')
                for row in rows:
                    cols = await row.query_selector_all('td')
                    if len(cols) == 2:
                        period = await cols[0].inner_text()
                        period = period.strip().rstrip(':')
                        value_text = await cols[1].inner_text()
                        value = self.clean_number(value_text.strip())
                        growth_data[category][period] = value
                        
            return pd.DataFrame(growth_data)
            
        except Exception as e:
            logging.error(f"Error extracting growth metrics: {e}")
            return pd.DataFrame()

    def get_key_metrics(self, pl_data: pd.DataFrame, bs_data: pd.DataFrame, cf_data: pd.DataFrame) -> Dict[str, float]:
        """Extract key financial metrics from P&L, Balance Sheet, and Cash Flow data"""
        try:
            latest_year = pl_data.columns[-1]
            
            metrics = {
                'Revenue': pl_data.loc['Sales', latest_year],
                'Operating_Profit': pl_data.loc['Operating Profit', latest_year],
                'Net_Profit': pl_data.loc['Net Profit', latest_year],
                'EPS': pl_data.loc['EPS in Rs', latest_year],
                'OPM': pl_data.loc['OPM %', latest_year],
                'Total_Assets': bs_data.loc['Total Assets', latest_year],
                'Total_Liabilities': bs_data.loc['Total Liabilities', latest_year],
                'Net_Worth': bs_data.loc['Net Worth', latest_year],
                'Book_Value': bs_data.loc['Book Value', latest_year] if 'Book Value' in bs_data.index else None,
                'Debt_Equity': bs_data.loc['Debt/Equity', latest_year] if 'Debt/Equity' in bs_data.index else None,
                'Operating_Cash_Flow': cf_data.loc['Cash from Operating Activity', latest_year],
                'Investing_Cash_Flow': cf_data.loc['Cash from Investing Activity', latest_year],
                'Financing_Cash_Flow': cf_data.loc['Cash from Financing Activity', latest_year],
                'Net_Cash_Flow': cf_data.loc['Net Cash Flow', latest_year],
                'FCF': cf_data.loc['Cash from Operating Activity', latest_year] - 
                       abs(cf_data.loc['Fixed assets purchased', latest_year]) if 'Fixed assets purchased' in cf_data.index else None
            }
            
            return {k: v for k, v in metrics.items() if v is not None}
            
        except Exception as e:
            logging.error(f"Error extracting key metrics: {e}")
            return {}

    async def scrape_company(self, page, ticker: str) -> Dict[str, pd.DataFrame]:
        """Main method to scrape company data using Playwright"""
        try:
            # Navigate to company page
            url = f"{self.base_url}{ticker}/"
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            # Expand all sections first
            await self.expand_sections(page)
            
            # Extract data from different sections
            pl_data = await self.extract_table_data(page, 'profit-loss')
            bs_data = await self.extract_table_data(page, 'balance-sheet')
            cf_data = await self.extract_table_data(page, 'cash-flow')
            growth_metrics = await self.extract_growth_metrics(page)
            
            # Get key metrics
            key_metrics = self.get_key_metrics(pl_data, bs_data, cf_data)
            key_metrics_df = pd.DataFrame([key_metrics]).T
            
            return {
                'profit_loss': pl_data,
                'balance_sheet': bs_data,
                'cash_flow': cf_data,
                'growth_metrics': growth_metrics,
                'key_metrics': key_metrics_df
            }
            
        except Exception as e:
            logging.error(f"Error scraping {ticker}: {e}")
            return {}

async def main():
    # Initialize scraper
    scraper = FinancialScraperPlaywright()
    
    # List of companies to scrape
    companies = ['ARE&M']  # Add more tickers as needed
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)  # Changed to headless=False to see the interactions
    context = await browser.new_context()
    page = await context.new_page()
    
    try:
        for ticker in companies:
            try:
                print(f"\nScraping data for {ticker}...")
                
                # Scrape company data
                data = await scraper.scrape_company(page, ticker)
                
                if data:
                    # Save to database
                    scraper.save_to_database(data, ticker)
                    
                    # Print key metrics
                    print(f"\nKey metrics for {ticker}:")
                    print(data['key_metrics'])
                
                # Add delay between requests
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                logging.error(f"Error processing {ticker}: {e}")
                print(f"Error processing {ticker}: {e}")
                
    finally:
        # Close browser
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())