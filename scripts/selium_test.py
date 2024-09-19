from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup

chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


# Initialize the WebDriver
driver = webdriver.Chrome(options=chrome_options)

# Open the webpage
url = "https://www.screener.in/company/ARE&M/"
driver.get(url)

# Wait for the page to load
time.sleep(3)  # Adjust this as necessary

# Click the "+" button to reveal hidden data
# Adjust the locator as necessary to match the actual "+" button
plus_button = driver.find_element(By.CSS_SELECTOR, "button.button-plain")  # Replace with the correct CSS selector or XPath
plus_button.click()

# Wait for the content to load after clicking
time.sleep(2)  # Adjust this as necessary

# Get the page source after the click
page_source = driver.page_source

# Parse with BeautifulSoup
soup = BeautifulSoup(page_source, 'html.parser')

# Now you can locate and scrape the Sales Growth data
# For example:
sales_growth = soup.find_all('tr', string=re.compile(r"Sales Growth %", re.IGNORECASE))

# Extract the data as required
for growth in sales_growth:
    print(growth.get_text(strip=True))

# Close the driver
driver.quit()
