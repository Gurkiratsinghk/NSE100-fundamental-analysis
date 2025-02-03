from playwright.async_api import async_playwright
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
import time
import re
from pathlib import Path
import sqlite3
import sys

class FinancialScraperPlaywright:
    def __init__(self):
        """Initialize the scraper with necessary configurations"""
        self.base_url = "https://www.screener.in/company/"
        self.setup_data_directory()
        self.setup_logging()
        self.setup_database()
        
    def setup_data_directory(self):
        """Setup necessary directories for data and logs"""
        # Use the same directory structure as FinancialScraperPlaywright
        self.data_dir = Path(__file__).parent.parent / 'scraper_v1.2_data'
        self.data_dir.mkdir(exist_ok=True)
        
        # Create logs directory
        self.log_dir = self.data_dir / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.log_dir / f'company_import_log_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.info("Logging setup completed")
        
    def setup_database(self):
        """Setup SQLite database and create necessary tables"""
        try:
            self.db_path = self.data_dir / 'financial_data.db'
            
            with sqlite3.connect(str(self.db_path)) as conn:
                c = conn.cursor()
                
                # Create companies table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS companies (
                        ticker TEXT PRIMARY KEY,
                        company_name text,
                        industry text,
                        last_updated TIMESTAMP
                    )
                ''')
                
                # Create financial_data table with proper constraints
                c.execute('''
                    CREATE TABLE IF NOT EXISTS financial_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticker TEXT,
                        data_type TEXT,
                        date TEXT,
                        metric TEXT,
                        value REAL,
                        UNIQUE(ticker, data_type, date, metric)
                    )
                ''')
                
                conn.commit()
                logging.info("Database setup completed successfully")
                
        except Exception as e:
            logging.error(f"Database setup error: {e}")
            raise

    async def save_to_database(self, data: Dict[str, pd.DataFrame], ticker: str):
        """Save financial data to SQLite database"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Update companies table
                conn.execute(
                    "INSERT OR REPLACE INTO companies (ticker, last_updated) VALUES (?, ?)",
                    (ticker, datetime.now().isoformat())
                )
                
                # Process each dataframe
                for data_type, df in data.items():
                    if not isinstance(df, pd.DataFrame):
                        logging.warning(f"Skipping {data_type} - not a DataFrame")
                        continue
                        
                    # Convert DataFrame to database records
                    records = []
                    
                    if df.empty:
                        logging.warning(f"Empty DataFrame for {data_type}")
                        continue
                    
                    if data_type == 'growth_metrics':
                        # Special handling for growth metrics
                        for _, row in df.iterrows():
                            records.append((
                                ticker,
                                data_type,
                                str(row['date']),  # Keep as string
                                str(row['metric']),  # Keep as string
                                float(row['value']) if pd.notnull(row['value']) else None
                            ))
                    else:
                        # Handle regular financial data
                        if isinstance(df.index, pd.Index):
                            df_processed = df.reset_index()
                        else:
                            df_processed = df
                        
                        for _, row in df_processed.iterrows():
                            metric = str(row.iloc[0])  # First column is metric name
                            for col, value in row.iloc[1:].items():
                                if pd.notnull(value):
                                    try:
                                        float_value = float(value)
                                        records.append((
                                            ticker,
                                            data_type,
                                            str(col),
                                            metric,
                                            float_value
                                        ))
                                    except (ValueError, TypeError):
                                        logging.warning(f"Skipping non-numeric value: {value} for {metric}")
                    
                    # Batch insert records
                    if records:
                        conn.executemany('''
                            INSERT OR REPLACE INTO financial_data 
                            (ticker, data_type, date, metric, value)
                            VALUES (?, ?, ?, ?, ?)
                        ''', records)
                
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

    async def expand_all_sections(self, page):
        """Click on all '+' buttons to expand sections before scraping"""
        try:
            logging.info("Starting to expand all sections")
            await page.wait_for_load_state('networkidle')
            
            # Find all buttons with the specific class and + icon
            buttons = await page.query_selector_all('button.button-plain:has(span.blue-icon)')
            total_buttons = len(buttons)
            buttons_to_process = buttons[:19]  # Take only first 19 elements
            
            logging.info(f"Found {total_buttons} buttons, processing first 19")
            
            for button in buttons_to_process:
                try:
                    # Get button text to log which section we're expanding
                    button_text = await button.text_content()
                    logging.info(f"Expanding section: {button_text.strip()}")
                    
                    await button.click()
                    # Wait for section to expand
                    await page.wait_for_timeout(1000)
                    
                except Exception as e:
                    logging.error(f"Error expanding section: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error in expand_all_sections: {e}")

    async def extract_table_data(self, page, section_id: str) -> pd.DataFrame:
        """Extract data from a specific section using Playwright selectors"""
        try:
            logging.info(f"Extracting data from section: {section_id}")
            
            # Wait for the section to be visible
            section = await page.wait_for_selector(f'section#{section_id}')
            if not section:
                raise ValueError(f"{section_id} section not found")
            
            # Extract headers
            headers = ['Metric']
            header_elements = await page.query_selector_all(f'section#{section_id} table.data-table th')
            for header in header_elements[1:]:
                header_text = await header.inner_text()
                headers.append(header_text.strip())
            
            # Extract rows
            rows = []
            row_elements = await page.query_selector_all(f'section#{section_id} table.data-table tbody tr')
            
            for row_element in row_elements:
                row = []
                metric_element = await row_element.query_selector('td.text') or await row_element.query_selector('td:first-child')
                metric_name = await metric_element.inner_text()
                metric_name = re.sub(r'\s*[-+]\s*$', '', metric_name.strip())
                row.append(metric_name)
                
                value_elements = await row_element.query_selector_all('td:not(:first-child)')
                for value_element in value_elements:
                    value_text = await value_element.inner_text()
                    value = self.clean_number(value_text.strip())
                    row.append(value)
                
                rows.append(row)
            
            df = pd.DataFrame(rows, columns=headers)
            df.set_index('Metric', inplace=True)
            
            logging.info(f"Successfully extracted {len(rows)} rows from {section_id}")
            return df
            
        except Exception as e:
            logging.error(f"Error extracting {section_id} data: {e}")
            return pd.DataFrame()
        
    async def extract_growth_metrics(self, page) -> pd.DataFrame:
        """Extract growth metrics tables using Playwright selectors"""
        try:
            growth_data = []  # Change to list to store records
            tables = await page.query_selector_all('table.ranges-table')
            
            for table in tables:
                period_element = await table.query_selector('th')
                period = await period_element.inner_text()
                period = period.strip()
                
                rows = await table.query_selector_all('tr:not(:first-child)')
                for row in rows:
                    cols = await row.query_selector_all('td')
                    if len(cols) == 2:
                        category = await cols[0].inner_text()
                        category = category.strip().rstrip(':')  # This will be '10 Years' or '5 Years'
                        value_text = await cols[1].inner_text()
                        value = self.clean_number(value_text.strip())
                        
                        # Create a record with period as metric and period as date
                        growth_data.append({
                            'metric': category,
                            'date': period,
                            'value': value
                        })
        
            # Convert to DataFrame
            df = pd.DataFrame(growth_data)
            return df
            
        except Exception as e:
            logging.error(f"Error extracting growth metrics: {e}")
            return pd.DataFrame()

    async def scrape_company(self, page, ticker: str) -> Dict[str, pd.DataFrame]:
        """Main method to scrape company data using Playwright"""
        try:
            # Navigate to company page
            url = f"{self.base_url}{ticker}/"
            logging.info(f"Navigating to {url}")
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            # Expand all sections once before starting extraction
            logging.info("Expanding all sections")
            await self.expand_all_sections(page)
            
            # Extract data from each section
            logging.info("Starting data extraction")
            data = {}
            
            # Extract profit & loss data
            data['profit_loss'] = await self.extract_table_data(page, 'profit-loss')
            
            # Extract balance sheet data
            data['balance_sheet'] = await self.extract_table_data(page, 'balance-sheet')
            
            # Extract cash flow data
            data['cash_flow'] = await self.extract_table_data(page, 'cash-flow')

            # Extract growth metrics data
            data['growth_metrics'] = await self.extract_growth_metrics(page)
            
            # Calculate and add key metrics if we have the required data
            if all(key in data for key in ['profit_loss', 'balance_sheet', 'cash_flow', 'growth_metrics']):
                key_metrics = self.extract_key_metrics(
                    data['balance_sheet'],
                    data['cash_flow'],
                    data['growth_metrics']
                )
                data['key_metrics'] = pd.DataFrame([key_metrics]).T
            
            logging.info(f"Successfully scraped data for {ticker}")
            return data
            
        except Exception as e:
            logging.error(f"Error scraping {ticker}: {e}")
            return {}

    def extract_key_metrics(self, bs_data, cf_data, growth_data):
        try:
            # Check if DataFrames are empty
            if bs_data.empty or cf_data.empty:
                logging.warning("Balance sheet or cash flow data is empty")
                return {}

            # Get available columns and find most recent period
            available_columns = bs_data.columns.tolist()
            if not available_columns:
                logging.warning("No columns found in balance sheet data")
                return {}
                
            latest_year = available_columns[0]  # Use first available column instead of hardcoding 'TTM'
            logging.info(f"Using {latest_year} as the latest period")

            metrics = {
                'Net_Worth': bs_data.loc['Net Worth', latest_year] if 'Net Worth' in bs_data.index else None,
                'Operating_Cash_Flow': cf_data.loc['Cash from Operating Activity', latest_year] if 'Cash from Operating Activity' in cf_data.index else None,
                'Net_Cash_Flow': cf_data.loc['Net Cash Flow', latest_year] if 'Net Cash Flow' in cf_data.index else None
            }

            # Add growth metrics if growth_data is not empty
            if isinstance(growth_data, pd.DataFrame) and not growth_data.empty:
                # Add growth metrics logic here
                pass
            
            # Filter out None values and return
            return {k: v for k, v in metrics.items() if pd.notna(v)}
                
        except Exception as e:
            logging.error(f"Error extracting key metrics: {e}")
            return {}

    async def expand_section(self, page, section_name):
        """Expand a collapsible section with minimal overhead"""
        try:
            # Simple section selector
            section_xpath = f"//div[contains(@class, 'flex-row')]//span[contains(text(), '{section_name}')]"
            section = await page.wait_for_selector(section_xpath, timeout=2000)
            
            if not section:
                return False
    
            # Single click attempt
            button = await section.query_selector("button")
            if button:
                await button.click(timeout=2000)
                await page.wait_for_timeout(200)  # Small delay for animation
                
            return True
    
        except Exception as e:
            logging.error(f"Error expanding {section_name}: {e}")
            return False
    
    async def scrape_shareholding(self, page):
        """Scrape shareholding data sequentially"""
        sections = ['Promoters', 'FIIs', 'DIIs', 'Public']
        
        for section in sections:
            await self.expand_section(page, section)
            await page.wait_for_timeout(200)  # Small delay between sections

async def main(companies: List[str]):
    scraper = FinancialScraperPlaywright()
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    
    try:
        for ticker in companies:
            try:
                print(f"\nScraping data for {ticker}...")
                
                # Scrape company data
                data = await scraper.scrape_company(page, ticker)
                
                if isinstance(data, dict):
                    # Save to database
                    await scraper.save_to_database(data, ticker)
                    
                    # Print confirmation
                    print(f"Data for {ticker} has been saved to database")
                    
                    # Print key metrics if available
                    key_metrics = data.get('key_metrics', {})
                    if isinstance(key_metrics, dict) and key_metrics:
                        print(f"Key metrics for {ticker}: {key_metrics}")
                    else:
                        logging.warning(f"Empty DataFrame for key_metrics")
                else:
                    print(f"No valid data found for {ticker}")
            except Exception as e:
                logging.error(f"Error processing {ticker}: {str(e)}")
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    import asyncio
    import pandas as pd

    companies = ['ARE&M']
    asyncio.run(main(companies))