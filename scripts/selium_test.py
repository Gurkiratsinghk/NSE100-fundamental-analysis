from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import re 

chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")


# Initialize the WebDriver
driver = webdriver.Chrome(options=chrome_options)

# Open the webpage
url = "https://www.screener.in/company/ARE&M/"
driver.get(url) # Debug line

# Wait for the page to load
time.sleep(3)  # Adjust this as necessary

# Click the "+" button to reveal hidden data
# Adjust the locator as necessary to match the actual "+" button
# Wait for the button to be clickable
wait = WebDriverWait(driver, 15)
plus_button = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//section[@id='profit-loss']//button[contains(., 'Sales')]")
))
driver.execute_script("arguments[0].click();", plus_button)
print('button clicked') # Debug line

# Wait for the content to load after clicking
time.sleep(1)  # Adjust this as necessary

# Get the page source after the click
page_source = driver.page_source

# Parse with BeautifulSoup
soup = BeautifulSoup(page_source, 'html.parser')

# Find the section and div
pl_section = soup.find('section', id='profit-loss')
div = pl_section.find('div', class_='responsive-holder fill-card-width')

rows = div.find_all('tr', class_='stripe')

# Iterate through rows to find the one containing "Sales Growth %"
sales_growth_row = None
for row in rows:
    if row.find('td', class_='text') and "Sales Growth %" in row.find('td', class_='text').text:
        sales_growth_row = row
        break

# If the row is found, you can extract the desired values
if sales_growth_row:
    sales_growth_data = [td.text for td in sales_growth_row.find_all('td')]
    print(sales_growth_data)  # This will give you a list of the sales growth percentages
else:
    print("Sales Growth row not found.")

# Close the driver
driver.quit()

