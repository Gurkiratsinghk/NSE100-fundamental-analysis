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
driver.get(url)

# Wait for the page to load
time.sleep(3)  # Adjust this as necessary

# Function to click the "+" button and scrape data
def click_and_scrape(button_text):
    wait = WebDriverWait(driver, 15)
    plus_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f"//section[@id='profit-loss']//button[contains(., '{button_text}')]")
    ))
    driver.execute_script("arguments[0].click();", plus_button)
    time.sleep(1)  # Adjust this as necessary
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    pl_section = soup.find('section', id='profit-loss')
    div = pl_section.find('div', class_='responsive-holder fill-card-width')
    rows = div.find_all('tr', class_='stripe')
    return rows

# Function to find and print data for a specific row
def find_and_print_data(rows, row_text):
    for row in rows:
        if row.find('td', class_='text') and row_text in row.find('td', class_='text').text:
            data = [td.text for td in row.find_all('td')]
            print(f"{row_text} data: {data}")
            return
    print(f"{row_text} row not found.")

# Click and scrape for each required row
for button_text, row_text in [("Sales", "Sales Growth %"), ("Expenses", "Expenses Growth %"), ("Other Income", "Other Income Growth %"), ("Net Profit", "Net Profit Growth %")]:
    rows = click_and_scrape(button_text)
    find_and_print_data(rows, row_text)

# Close the driver
driver.quit()