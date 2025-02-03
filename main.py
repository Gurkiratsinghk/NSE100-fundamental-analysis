from scripts import import_csv
from os import getcwd
from pathlib import Path

def main():
    try:
        # Initialize the company data manager
        manager = import_csv.CompanyDataManager()
        
        # Import company data
        path = getcwd()
        csv_path = f'{path}/NSE data/ind_nifty100list.csv'
        
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"Input CSV not found at {csv_path}")                            
        else:
            manager.import_company_data(csv_path)
        
        # Verify the import
        manager.verify_import()
        
        # Save a backup of the imported data
        manager.save_backup(csv_path=csv_path)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
