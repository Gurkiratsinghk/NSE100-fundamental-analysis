# Enteries 
------
### 10th Jan 2025
Scraping strategy shifted to Playwrite. The code output was better than `scrapeTest.py`. Currently `test_scrite_playwrite_v2.py` is being developed as final file. The code still needs to get sub-entries from the tables, which I came to believe would be easy with Playwrite. *The `.log` files needs to be moved into the respective data folder.*

# Things on-going
------

`Selium_test.py` is underway to mimic the button click to expand the sub-tables.

`scrape_financials.py` is the final script that is tasked with taking the `companies.csv` and scraping the fundamental data of the companies finances, and saving the data into `financials.csv`. 

`test_script.py` is used to test out changes for the `scrape_financials` on one company before implementing it for the NSE100

# Things done
------

`import_csv.py` takes the `ind_nifty100list.csv` because scraping the nse website was not possible, and the alternate solution were hectic.

the `import_csv.py` gives the companies name with their tickers and their industry sector.

------
# Project Overview
------

A Python-based tool in Replit to scrape financial data for NIFTY100 companies from the website "https://www.screener.in". The project involves storing the data in a structured format using Pandas DataFrames for future fundamental analysis.

Steps Taken

## 1. Data Setup:
* CSV Import: import a CSV file (NSE data/nifty100_companies.csv) containing company names, industry sectors, and stock tickers for NIFTY100 companies.
* DataFrame Creation: The relevant columns (Company Name, Industry, and Symbol) are extracted and stored in a Pandas DataFrame (NSE data/companies.csv).


## 2. Web Scraping:
* Scrape Financial Data: Write a script (scrape_financials.py) to scrape financial data of each company's page on Screener.in. But there are a lot of improvements that needs to be done here. 
* Handling Errors: Implemented error handling to manage cases where certain data might be missing or the HTML structure doesn't match expectations.
* Dynamic Extraction: We dynamically extracted key financial metrics (like Sales, Expenses, Operating Profit, etc.) for each year listed on the website.
* Data Storage: The scraped data was stored in a Pandas DataFrame and then exported to a CSV file (financials.csv) for future analysis. [This is to be implemented]


## 3. Directory Structure:
* Data: Created a “data/“ directory to store CSV files.
* Scripts: Stored Python scripts in a “scripts/“ directory.
