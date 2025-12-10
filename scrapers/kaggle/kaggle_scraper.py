import requests
from bs4 import BeautifulSoup

class KaggleScraper:
    def __init__(self, base_url="https://www.kaggle.com/datasets"):
        self.base_url = base_url

    def fetch_page(self):
        response = requests.get(self.base_url)
        response.raise_for_status()
        return response.text

    def parse_datasets(self, html):
        soup = BeautifulSoup(html, "html.parser")
        titles = [a.get_text(strip=True) for a in soup.select("a.sc-1x5rzg1-1")]
        return titles

    def scrape(self):
        html = self.fetch_page()
        datasets = self.parse_datasets(html)
        return datasets
