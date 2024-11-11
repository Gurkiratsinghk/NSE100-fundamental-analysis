import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
import time
import re

class FinancialScraper:
    def __init__(self):
        """Initialize the scraper with necessary configurations"""
        self.base_url = "https://www.screener.in/company/"
        self.setup_logging()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            filename=f'scraping_log_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def clean_number(self, value: str) -> Optional[float]:
        """Clean and convert string numbers to float"""
        try:
            # Remove ₹, Cr., %, and commas, then convert to float
            value = str(value)
            value = value.replace('₹', '').replace('Cr.', '').replace('%', '').replace(',', '').strip()
            return float(value) if value and value != '-' else None
        except (ValueError, AttributeError):
            logging.warning(f"Could not convert value: {value}")
            return None

    def fetch_company_data(self, ticker: str) -> str:
        """Fetch HTML content from screener.in"""
        try:
            url = f"{self.base_url}{ticker}/"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error fetching data for {ticker}: {e}")
            raise

    def extract_section_data(self, soup: BeautifulSoup, section_id: str) -> pd.DataFrame:
        """Extract data from a specific section (P&L, Balance Sheet, or Cash Flow)"""
        try:
            section = soup.find('section', id=section_id)
            if not section:
                raise ValueError(f"{section_id} section not found")

            table = section.find('table', class_='data-table')
            
            # Extract headers (years)
            headers = ['Metric']
            for th in table.find('tr').find_all('th')[1:]:  # Skip first th (empty)
                headers.append(th.text.strip())

            # Extract rows
            rows = []
            for tr in table.find('tbody').find_all('tr'):
                row = []
                # Get metric name (remove any JS buttons)
                metric_td = tr.find('td', class_='text')
                if metric_td:
                    metric_name = metric_td.text.strip()
                else:
                    metric_name = tr.find('td').text.strip()
                    
                # Clean up the metric name by removing any button text indicators
                metric_name = re.sub(r'\s*[-+]\s*$', '', metric_name)
                row.append(metric_name)
                
                # Get values for each year
                for td in tr.find_all('td')[1:]:  # Skip first td (metric name)
                    value = self.clean_number(td.text.strip())
                    row.append(value)
                
                rows.append(row)

            # Create DataFrame
            df = pd.DataFrame(rows, columns=headers)
            df.set_index('Metric', inplace=True)
            return df

        except Exception as e:
            logging.error(f"Error extracting {section_id} data: {e}")
            return pd.DataFrame()

    def extract_growth_metrics(self, soup: BeautifulSoup) -> pd.DataFrame:
        """Extract growth metrics tables"""
        try:
            growth_tables = soup.find_all('table', class_='ranges-table')
            growth_data = {}
            
            for table in growth_tables:
                category = table.find('th').text.strip()
                growth_data[category] = {}
                
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) == 2:
                        period = cols[0].text.strip().rstrip(':')
                        value = self.clean_number(cols[1].text.strip())
                        growth_data[category][period] = value

            return pd.DataFrame(growth_data)
        except Exception as e:
            logging.error(f"Error extracting growth metrics: {e}")
            return pd.DataFrame()

    def get_key_metrics(self, pl_data: pd.DataFrame, bs_data: pd.DataFrame, cf_data: pd.DataFrame) -> Dict[str, float]:
        """Extract key financial metrics from P&L, Balance Sheet, and Cash Flow data"""
        try:
            latest_year = pl_data.columns[-1]  # Get the most recent year
            
            metrics = {
                # P&L Metrics
                'Revenue': pl_data.loc['Sales', latest_year],
                'Operating_Profit': pl_data.loc['Operating Profit', latest_year],
                'Net_Profit': pl_data.loc['Net Profit', latest_year],
                'EPS': pl_data.loc['EPS in Rs', latest_year],
                'OPM': pl_data.loc['OPM %', latest_year],
                
                # Balance Sheet Metrics
                'Total_Assets': bs_data.loc['Total Assets', latest_year],
                'Total_Liabilities': bs_data.loc['Total Liabilities', latest_year],
                'Net_Worth': bs_data.loc['Net Worth', latest_year],
                'Book_Value': bs_data.loc['Book Value', latest_year] if 'Book Value' in bs_data.index else None,
                'Debt_Equity': bs_data.loc['Debt/Equity', latest_year] if 'Debt/Equity' in bs_data.index else None,
                
                # Cash Flow Metrics
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

    def save_to_csv(self, data: Dict[str, pd.DataFrame], company_name: str):
        """Save financial data to CSV files"""
        timestamp = datetime.now().strftime("%Y%m%d")
        
        try:
            for key, df in data.items():
                filename = f'{company_name}_{key}_{timestamp}.csv'
                df.to_csv(filename)
                logging.info(f"Successfully saved {key} for {company_name}")
            
        except Exception as e:
            logging.error(f"Error saving CSV files: {e}")

    def scrape_company(self, ticker: str) -> Dict[str, pd.DataFrame]:
        """Main method to scrape company data"""
        try:
            # Fetch HTML content
            html_content = self.fetch_company_data(ticker)
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract data from different sections
            pl_data = self.extract_section_data(soup, 'profit-loss')
            bs_data = self.extract_section_data(soup, 'balance-sheet')
            cf_data = self.extract_section_data(soup, 'cash-flow')
            growth_metrics = self.extract_growth_metrics(soup)

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

def main():
    # Initialize scraper
    scraper = FinancialScraper()
    
    # List of companies to scrape
    companies = ['ARE&M']  # Add more tickers as needed
    
    for ticker in companies:
        try:
            print(f"\nScraping data for {ticker}...")
            
            # Scrape company data
            data = scraper.scrape_company(ticker)
            
            if data:
                # Save to CSV
                scraper.save_to_csv(data, ticker)
                
                # Print key metrics
                print(f"\nKey metrics for {ticker}:")
                print(data['key_metrics'])
                
            # Add delay between requests
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"Error processing {ticker}: {e}")
            print(f"Error processing {ticker}: {e}")

if __name__ == "__main__":
    main()