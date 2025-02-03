'''
The script also needs to check if the database has only 100 companies. 
As NSE 100 is updated every quarter, the script should be able to update the database with the latest list of companies.
'''

import pandas as pd
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import sys

class CompanyDataManager:
    def __init__(self):
        """Initialize the company data manager with necessary configurations"""
        self.setup_directories()
        self.setup_logging()
        self.setup_database()

    def setup_directories(self):
        """Setup necessary directories for data and logs"""
        # Use the same directory structure as FinancialScraperPlaywright
        self.data_dir = Path(__file__).parent.parent / 'scraper_v1.2_data'  # Change this to 'Database' in the final version
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
                        company_name TEXT,
                        industry TEXT,
                        last_updated TIMESTAMP
                    )
                ''')
                
                # Create financial_data table (maintained for consistency)
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

    def import_company_data(self, csv_path: str):
        """Import company data from CSV file to database"""
        try:
            # Read the CSV file
            logging.info(f"Reading company data from {csv_path}")
            df = pd.read_csv(csv_path, usecols=['Company Name', 'Industry', 'Symbol'])
            
            # Connect to database
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Prepare data for insertion
                companies_data = []
                current_time = datetime.now().isoformat()
                
                for _, row in df.iterrows():
                    companies_data.append((
                        row['Symbol'],  # ticker
                        row['Company Name'],
                        row['Industry'],
                        current_time
                    ))
                
                # Insert or update company records
                cursor.executemany('''
                    INSERT OR REPLACE INTO companies 
                    (ticker, company_name, industry, last_updated)
                    VALUES (?, ?, ?, ?)
                ''', companies_data)
                
                conn.commit()
                
                # Log success
                logging.info(f"Successfully imported {len(companies_data)} companies")
                
                # Log summary of companies by industry
                industry_summary = df.groupby('Industry').size()
                logging.info("\nIndustry-wise company distribution:")
                for industry, count in industry_summary.items():
                    logging.info(f"{industry}: {count} companies")
                
        except Exception as e:
            logging.error(f"Error importing company data: {e}")
            raise

    def verify_import(self):
        """Verify the imported data"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM companies")
                total_count = cursor.fetchone()[0]
                
                # Get sample of records
                cursor.execute("""
                    SELECT ticker, company_name, industry, last_updated 
                    FROM companies 
                    LIMIT 5
                """)
                sample_records = cursor.fetchall()
                
                logging.info(f"\nVerification Results:")
                logging.info(f"Total companies in database: {total_count}")
                logging.info("\nSample records:")
                for record in sample_records:
                    logging.info(f"Ticker: {record[0]}, Company: {record[1]}, Industry: {record[2]}")
                
        except Exception as e:
            logging.error(f"Error verifying import: {e}")
            raise

    def save_backup(self, csv_path: str):
        """Save a backup of the imported data"""
        try:
            # Create backup directory path properly
            backup_dir = Path(self.data_dir) / 'NSE data'
            backup_file = backup_dir / 'companies.csv'
            
            # Create directories if they don't exist
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Read and save CSV
            pd.read_csv(
                csv_path, 
                usecols=['Company Name', 'Industry', 'Symbol']
            ).to_csv(
                backup_file,
                index=False
            )
            logging.info(f"Backup CSV saved to {backup_file}")
        
        except Exception as e:
            logging.error(f"Backup execution error: {e}")
            raise

def main():
    try:
        # Initialize the company data manager
        manager = CompanyDataManager()
        
        # Use absolute path for input CSV
        csv_path = Path(__file__).parent.parent / 'NSE data' / 'ind_nifty100list.csv'
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Input CSV not found at {csv_path}")
            
        # Import company data
        manager.import_company_data(str(csv_path))
        
        # Verify the import
        manager.verify_import()

        # Save a backup of the imported data
        manager.save_backup(str(csv_path))

    except Exception as e:
        logging.error(f"Main execution error: {e}")
        raise

if __name__ == "__main__":
    main()