from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from urllib.parse import urljoin
import time

BASE_URL = "https://www.kaggle.com"


class KaggleScraperSelenium:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # run in background
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=chrome_options)

    def build_search_url(self, term: str) -> str:
        encoded = quote_plus(term)
        return f"https://www.kaggle.com/search?q={encoded}+in%3Adatasets+sortBy%3Adate+date%3A90"  # limit to datasets added the last 90 days

    def fetch_page(self, term: str) -> str:
        url = self.build_search_url(term)
        self.driver.get(url)

        # wait for JS to render the dataset lists (or none if the query has no results)
        wait = WebDriverWait(self.driver, 2)
        try:
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div > ul > li")))
        except TimeoutException:
            return None # abort-no data
        return self.driver.page_source

    def parse_datasets(self, html: str, results: list):
        soup = BeautifulSoup(html, "html.parser")
        target_ul = None

        for ul in soup.find_all("ul"):
            parent = ul.parent
            # there is only one other ul, which is nested in a nav
            if parent and parent.name == "div":
                target_ul = ul
                break

        if not target_ul:
            return

        for li in target_ul.find_all("li", recursive=False):
            a = li.find("a", href=True)
            link = urljoin(BASE_URL, a["href"]) if a else None
            title = a.get("aria-label") if a and a.get("aria-label") else None

            img = li.find("img", src=True)
            thumbnail = img["src"] if img else None

            date_span = li.find("span", attrs={"title": True})
            date_str = date_span["title"] if date_span else None

            results.append(
                {
                    "title": title,
                    "link": link,
                    "thumbnail": thumbnail,
                    "date": date_str,
                }
            )
        return

    def parse_num_of_pages(self, html: str) -> int:
        soup = BeautifulSoup(html, "html.parser")

        nav = soup.find("nav")
        if not nav:
            return 0

        ul = nav.find("ul")
        if not ul:
            return 0

        li_items = ul.find_all("li", recursive=False)
        # in therory ther should always be 3 one prev, next and the current page, even if prev, next may not be visible
        if len(li_items) < 3:
            return 1 if len(li_items) > 0 else 0

        return len(li_items) - 2

    def click_next_button(self, pages: int, timeout=2):
        try:
            # wait until the pagination <ul> exists
            ul = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav > ul"))
            )

            # get all direct <li> children
            li_items = ul.find_elements(By.CSS_SELECTOR, "li")
            if not li_items or len(li_items) < 3:
                # fewer than 3 <li> → no next button
                return False
            # use pages as sanity check
            if (len(li_items)-2) != pages:
                return False
            # last <li> = next button
            next_li = li_items[len(li_items)-1]
            next_btn = next_li.find_element(By.TAG_NAME, "button")
            # check if disabled
            if next_btn.get_attribute("disabled") is not None:
                return False

            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(next_btn))
            self.driver.execute_script("arguments[0].click();", next_btn)

            time.sleep(0.4)
            wait = WebDriverWait(self.driver, 2)
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div > ul > li")))
            print("so far so good")
            return True

        except Exception:
            print(Exception)
            return False

    def scrape(self, term: str):
        results = []
        html = self.fetch_page(term)
        if html is None:
            return results
        pages = self.parse_num_of_pages(html)
        # give it proper time to load everything even if we find everything in the dom, we may not be able to navigate the page
        for _i in range(pages):
            self.parse_datasets(html, results)
            # we may be too fast for the button
            if(self.click_next_button(pages) is False):
                break
            html = self.driver.page_source
            
        return results

    def close(self):
        self.driver.quit()


# Usage example
# if __name__ == "__main__":
#     scraper = KaggleScraperSelenium()
#     results = scraper.scrape("house")
#     print("Datasets found:", results)
#     scraper.close()

# this is as of now for local testing only/ only runs locally
if __name__ == "__main__":
    scraper = KaggleScraperSelenium()
    try:
        results = scraper.scrape("car")
        print("\nDatasets found:")
        for idx, title in enumerate(results, 1):
            print(f"{idx}. {title}")
        print(f"\nTotal datasets: {len(results)}")
    finally:
        
        scraper.close()
