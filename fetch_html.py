import sqlite3
import codecs
conn = sqlite3.connect('nse_project/data/nse_fundamentals.db')
cursor = conn.cursor()
cursor.execute('SELECT symbol FROM companies WHERE id=1')
symbol = cursor.fetchone()[0]

import requests
from bs4 import BeautifulSoup
url = f"https://ticker.finology.in/company/{symbol}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'lxml')
block = soup.find('div', id='companyessentials')
containers = block.find_all('div', class_=lambda cls: cls and ('col-' in cls or 'mb-' in cls))
with open('dump.txt', 'w', encoding='utf-8') as f:
    for idx, div in enumerate(containers):
        small = div.find('small')
        p = div.find('p')
        if small and p:
            f.write(f"[{idx}] small: {small.get_text(strip=True)!r} | p: {p.get_text(strip=True)!r} | classes: {div.get('class')}\n")
        f.write(f"raw html: {str(div)}\n")
