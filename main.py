import os

def main():
    # Run the CSV import script
    os.system("python scripts/import_csv.py")

    # Run the financial data scraping script
    os.system("python scripts/scrape_financials.py")

if __name__ == "__main__":
    main()
