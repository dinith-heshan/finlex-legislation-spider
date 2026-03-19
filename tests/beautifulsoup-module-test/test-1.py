import requests
from bs4 import BeautifulSoup

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
        "FinlexSpider/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
})

r = requests.get("https://httpbin.org",  timeout=10)

soup = BeautifulSoup(r.text, "lxml")

print(soup.prettify())