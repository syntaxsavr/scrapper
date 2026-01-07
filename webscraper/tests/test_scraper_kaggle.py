from scrapers.kaggle.scraper_kaggle import KaggleScraperSelenium
from webscraper.tasks import scrape_kaggle_task

from unittest.mock import patch, MagicMock
from django.test import TestCase

def make_scraper_with_mock_driver():
    mock_driver = MagicMock()
    with patch("scraper.kaggle.webdriver.Chrome", return_value=mock_driver):
        scraper = KaggleScraperSelenium()
    return scraper, mock_driver


class ScraperKaggleTests(TestCase):

    def setUp(self):
        self.scraper = KaggleScraperSelenium()

    def tearDown(self):
        self.scraper.close()

    def test_url_builder(self):
        url = self.scraper.build_search_url("cars")
        self.assertEqual(url, "https://www.kaggle.com/search?q=cars+in%3Adatasets+sortBy%3Adate+date%3A90")

        url = self.scraper.build_search_url(" ca rs ")
        self.assertEqual(url, "https://www.kaggle.com/search?q=+ca+rs++in%3Adatasets+sortBy%3Adate+date%3A90")

        url = self.scraper.build_search_url("1-@cars ")
        self.assertEqual(url, "https://www.kaggle.com/search?q=1-%40cars++in%3Adatasets+sortBy%3Adate+date%3A90")

        url = self.scraper.build_search_url("")
        self.assertEqual(url, "https://www.kaggle.com/search?q=+in%3Adatasets+sortBy%3Adate+date%3A90")


    def test_parse1(self):
         with open("webscraper/tests/kaggle_test1.html", encoding="utf-8") as file:
            results=[]
            self.scraper.parse_datasets(file.read(),results)
            file.close()
            self.assertEqual(len(results), 20)
            self.assertEqual(results[0]["link"], "https://www.kaggle.com/datasets/pyim59/mini-datasets")
            self.assertEqual(results[0]["thumbnail"], "https://storage.googleapis.com/kaggle-datasets-images/9205632/14413364/46bd7a04f2b2562e00ab2c331517d02a/dataset-thumbnail.png?t=2026-01-06-14-53-23")
            self.assertEqual(results[0]["title"], "Mini datasets")
            self.assertEqual(results[0]["date"], "Tue Jan 06 2026 15:51:20 GMT+0100 (Central European Standard Time)")

            self.assertEqual(results[19]["link"], "https://www.kaggle.com/datasets/mateosenna/brazil-real-estate-dataset-uberaba-properties")
            self.assertEqual(results[19]["thumbnail"], "https://storage.googleapis.com/kaggle-datasets-images/9153870/14337250/88c25f761e372f1ff769a79b45220fee/dataset-thumbnail.png?t=2025-12-29-23-49-56")
            self.assertEqual(results[19]["title"], "Brazil Real Estate Dataset – Uberaba Properties")
            self.assertEqual(results[19]["date"], "Wed Dec 31 2025 19:28:39 GMT+0100 (Central European Standard Time)")

    def test_parse2(self):
         with open("webscraper/tests/kaggle_test2.html", encoding="utf-8") as file:
            results=[]
            self.scraper.parse_datasets(file.read(),results)
            file.close()
            self.assertEqual(len(results), 15)
            self.assertEqual(results[14]["link"], "https://www.kaggle.com/datasets/canhquang/data-pcb")
            self.assertEqual(results[14]["thumbnail"], "https://storage.googleapis.com/kaggle-datasets-images/new-version-temp-images/default-backgrounds-61.png-21177671/dataset-thumbnail.png")
            self.assertEqual(results[14]["title"], "DATA_pcb")
            self.assertEqual(results[14]["date"], "Mon Dec 08 2025 12:52:39 GMT+0100 (Central European Standard Time)")
    
    def test_parse3(self):
         with open("webscraper/tests/kaggle_test3.html", encoding="utf-8") as file:
            results=[]
            self.scraper.parse_datasets(file.read(),results)
            file.close()
            self.assertEqual(len(results), 0)

    def test_parse_pages1(self):
         with open("webscraper/tests/kaggle_test1.html", encoding="utf-8") as file:
            length = self.scraper.parse_num_of_pages(file.read())
            file.close()
            self.assertEqual(length, 10)
    
    def test_parse_pages2(self):
         with open("webscraper/tests/kaggle_test2.html", encoding="utf-8") as file:
            length = self.scraper.parse_num_of_pages(file.read())
            file.close()
            self.assertEqual(length, 1)
    
    def test_parse_pages3(self):
         with open("webscraper/tests/kaggle_test3.html", encoding="utf-8") as file:
            length = self.scraper.parse_num_of_pages(file.read())
            file.close()
            self.assertEqual(length, 0)

    def test_scrape1(self):
         with open("webscraper/tests/kaggle_test1.html", encoding="utf-8") as file:
            results = []
            html = file.read()
            file.close()
            self.scraper.fetch_page = MagicMock(return_value=html)
            
            mock_driver = MagicMock()
            mock_driver.page_source = html
            self.scraper.driver = mock_driver

            self.scraper.click_next_button = MagicMock(return_value=True)
            
            results = self.scraper.scrape("test1_lim10", 10)
            self.assertEqual(len(results), 10)
            results = self.scraper.scrape("test1_lim1000", 1000)
            self.assertEqual(len(results), 200)
            results = self.scraper.scrape("test1_lim0", 0)
            self.assertEqual(len(results), 0)
            results = self.scraper.scrape("test1_lim0", -1)
            self.assertEqual(len(results), 200)

    def test_scrape2(self):
         with open("webscraper/tests/kaggle_test2.html", encoding="utf-8") as file:
            results = []
            html = file.read()
            file.close()
            self.scraper.fetch_page = MagicMock(return_value=html)

            mock_driver = MagicMock()
            mock_driver.page_source = html
            self.scraper.driver = mock_driver

            self.scraper.click_next_button = MagicMock(return_value=True)
            
            results = self.scraper.scrape("test2_lim200", 200)
            self.assertEqual(len(results), 15)
            results = self.scraper.scrape("test1_lim1000", 10)
            self.assertEqual(len(results), 10)
            results = self.scraper.scrape("test1_lim0", 0)
            self.assertEqual(len(results), 0)
            results = self.scraper.scrape("test1_lim0", -1)
            self.assertEqual(len(results), 15)
    
    def test_scrape3(self):
         with open("webscraper/tests/kaggle_test3.html", encoding="utf-8") as file:
            results = []
            html = file.read()
            file.close()
            self.scraper.fetch_page = MagicMock(return_value=html)

            mock_driver = MagicMock()
            mock_driver.page_source = html
            self.scraper.driver = mock_driver

            self.scraper.click_next_button = MagicMock(return_value=True)
            
            results = self.scraper.scrape("test2_lim200", 200)
            self.assertEqual(len(results), 0)
            results = self.scraper.scrape("test1_lim1000", 10)
            self.assertEqual(len(results), 0)
            results = self.scraper.scrape("test1_lim0", 0)
            self.assertEqual(len(results), 0)
            results = self.scraper.scrape("test1_lim0", -1)
            self.assertEqual(len(results), 0)

    @patch("webscraper.tasks.KaggleScraperSelenium")
    def test_scraper_task(self, mock_scraper_class):
         with open("webscraper/tests/kaggle_test1.html", encoding="utf-8") as file:
            results = []
            html = file.read()
            file.close()
            self.scraper.fetch_page = MagicMock(return_value=html)

            mock_driver = MagicMock()
            mock_driver.page_source = html
            self.scraper.driver = mock_driver

            self.scraper.click_next_button = MagicMock(return_value=True)

            mock_scraper_class.return_value = self.scraper
            
            # we loop over the same 20 items over and over thus only 20 added
            results = scrape_kaggle_task("test1_lim200", 200)
            self.assertEqual(results["query"], "test1_lim200")
            self.assertEqual(results["total_scraped"], 200)
            self.assertEqual(results["added"], 20)
            # added should be 0 because we try to add the same stuff again
            results = scrape_kaggle_task("test1_lim10", 10)
            self.assertEqual(results["query"], "test1_lim10")
            self.assertEqual(results["total_scraped"], 10)
            self.assertEqual(results["added"], 0)

            results = scrape_kaggle_task("test1_lim10", -1)
            self.assertEqual(results["query"], "test1_lim10")
            self.assertEqual(results["total_scraped"], 200)
            self.assertEqual(results["added"], 0)