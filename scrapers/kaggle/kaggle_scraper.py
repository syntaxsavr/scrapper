import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# beautiful soup and plain requests are not enough - the kaggle delivers a barebone site, everything is built by js later on.


class KaggleScraper:
    def __init__(self, base_url="https://www.kaggle.com"):
        self.base_url = base_url

    def build_search_url(self, term: str) -> str:
        if not term.strip():
            return f"{self.base_url}/datasets"

        encoded = quote_plus(term.strip())
        return f"{self.base_url}/search?q={encoded}+date%3A1"  # limit to results from last day

    def fetch_page(self, term: str):
        # response = requests.get(self.base_url)
        # response.raise_for_status()
        # return response.text
        url = self.build_search_url(term)
        # try to fake being a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en,de;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def parse_datasets(self, html):
        soup = BeautifulSoup(html, "html.parser")
        titles = [a.get_text(strip=True) for a in soup.select("a.sc-1x5rzg1-1")]
        return titles

    def scrape(self, term: str):
        html = self.fetch_page(term)
        datasets = self.parse_datasets(html)
        return datasets


if __name__ == "__main__":
    term = "houses"
    scraper = KaggleScraper()
    html = scraper.fetch_page(term)

    print("\n RAW HTML")
    print(html)

    print("\n PARSED TITLES")
    datasets = scraper.parse_datasets(html)

    for title in datasets:
        print("-", title)

    print(f"\nTotal parsed datasets: {len(datasets)}")
