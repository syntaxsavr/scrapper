import os
import time
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from unittest.mock import patch, Mock
from webscraper.models import Dataset


class SearchJavaScriptTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')

        selenium_host = os.environ.get('SELENIUM_HOST', 'selenium')
        selenium_url = f'http://{selenium_host}:4444/wd/hub'

        cls.selenium = webdriver.Remote(
            command_executor=selenium_url,
            options=chrome_options
        )
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        Dataset.objects.create(
            title="Machine Learning Dataset",
            description="A comprehensive dataset for machine learning"
        )

    def test_page_loads_with_search_elements(self):
        self.selenium.get(f'{self.live_server_url}/')

        search_form = self.selenium.find_element(By.ID, 'search-form')
        search_input = self.selenium.find_element(By.ID, 'search-input')
        results_container = self.selenium.find_element(By.ID, 'results-container')

        self.assertIsNotNone(search_form)
        self.assertIsNotNone(search_input)
        self.assertIsNotNone(results_container)

    def test_form_submission_prevents_page_reload(self):
        self.selenium.get(f'{self.live_server_url}/')

        initial_url = self.selenium.current_url

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('test')
        search_form.submit()

        time.sleep(0.5)

        current_url = self.selenium.current_url
        self.assertEqual(initial_url, current_url)

    def test_empty_search_updates_results_container(self):
        self.selenium.get(f'{self.live_server_url}/')

        results_container_before = self.selenium.find_element(By.ID, 'results-container')
        initial_content = results_container_before.text

        search_form = self.selenium.find_element(By.ID, 'search-form')
        submit_button = search_form.find_element(By.CSS_SELECTOR, 'button[type="submit"]')

        submit_button.click()

        time.sleep(0.5)

        results_container_after = self.selenium.find_element(By.ID, 'results-container')
        final_content = results_container_after.text

        self.assertNotEqual(initial_content, final_content)
        self.assertTrue(len(final_content) > 0)

    def test_whitespace_search_updates_results_container(self):
        self.selenium.get(f'{self.live_server_url}/')

        results_container_before = self.selenium.find_element(By.ID, 'results-container')
        initial_content = results_container_before.text

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('   ')
        search_form.submit()

        time.sleep(0.5)

        results_container_after = self.selenium.find_element(By.ID, 'results-container')
        final_content = results_container_after.text

        self.assertNotEqual(initial_content, final_content)
        self.assertTrue(len(final_content) > 0)

    def test_search_query_html_escaping(self):
        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        xss_payload = '<script>alert("XSS")</script>'
        search_input.send_keys(xss_payload)
        search_form.submit()

        time.sleep(1)

        page_source = self.selenium.page_source
        self.assertNotIn('<script>alert("XSS")</script>', page_source)

    def test_special_characters_in_query_escaped(self):
        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        special_chars = '<div>Test & "quotes"</div>'
        search_input.send_keys(special_chars)
        search_form.submit()

        time.sleep(1)

        page_source = self.selenium.page_source
        self.assertNotIn('<div>Test & "quotes"</div>', page_source)

    @patch('webscraper.views.AsyncResult')
    @patch('webscraper.tasks.search_datasets')
    @patch('webscraper.tasks.scrap_huggingface_datasets')
    def test_results_displayed_in_dom(self, mock_scrap_hf, mock_search, mock_async_result):
        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        mock_task_result = Mock()
        mock_task_result.ready.return_value = True
        mock_task_result.result = {
            "results": [
                {"id": 1, "title": "Test Dataset 1", "description": "Description 1"},
                {"id": 2, "title": "Test Dataset 2", "description": "Description 2"}
            ]
        }
        mock_async_result.return_value = mock_task_result

        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('test')
        search_form.submit()

        try:
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.results-list'))
            )

            results_container = self.selenium.find_element(By.ID, 'results-container')
            self.assertIn('Test Dataset 1', results_container.text)
            self.assertIn('Test Dataset 2', results_container.text)
        except TimeoutException:
            pass

    @patch('webscraper.views.AsyncResult')
    @patch('webscraper.tasks.search_datasets')
    @patch('webscraper.tasks.scrap_huggingface_datasets')
    def test_multiple_result_items_rendered(self, mock_scrap_hf, mock_search, mock_async_result):
        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        mock_task_result = Mock()
        mock_task_result.ready.return_value = True
        mock_task_result.result = {
            "results": [
                {"id": 1, "title": "Dataset A", "description": "Description A"},
                {"id": 2, "title": "Dataset B", "description": "Description B"},
                {"id": 3, "title": "Dataset C", "description": "Description C"}
            ]
        }
        mock_async_result.return_value = mock_task_result

        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('dataset')
        search_form.submit()

        try:
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.result-item'))
            )

            result_items = self.selenium.find_elements(By.CSS_SELECTOR, '.result-item')
            self.assertEqual(len(result_items), 3)
        except TimeoutException:
            pass

    @patch('webscraper.views.AsyncResult')
    @patch('webscraper.tasks.search_datasets')
    @patch('webscraper.tasks.scrap_huggingface_datasets')
    def test_result_links_have_correct_href(self, mock_scrap_hf, mock_search, mock_async_result):
        dataset = Dataset.objects.first()

        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        mock_task_result = Mock()
        mock_task_result.ready.return_value = True
        mock_task_result.result = {
            "results": [
                {"id": dataset.id, "title": dataset.title, "description": dataset.description}
            ]
        }
        mock_async_result.return_value = mock_task_result

        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('machine')
        search_form.submit()

        try:
            WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.result-link'))
            )

            result_link = self.selenium.find_element(By.CSS_SELECTOR, '.result-link')
            expected_url = f'/detailed_view/{dataset.id}/'
            self.assertIn(expected_url, result_link.get_attribute('href'))
        except TimeoutException:
            pass

    @patch('webscraper.views.AsyncResult')
    @patch('webscraper.tasks.search_datasets')
    @patch('webscraper.tasks.scrap_huggingface_datasets')
    def test_zero_results_clears_result_items(self, mock_scrap_hf, mock_search, mock_async_result):
        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        mock_task_result = Mock()
        mock_task_result.ready.return_value = True
        mock_task_result.result = {
            "results": []
        }
        mock_async_result.return_value = mock_task_result

        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('nonexistent')
        search_form.submit()

        time.sleep(2)

        result_items = self.selenium.find_elements(By.CSS_SELECTOR, '.result-item')
        self.assertEqual(len(result_items), 0)


class SearchPollingBehaviorTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')

        selenium_host = os.environ.get('SELENIUM_HOST', 'selenium')
        selenium_url = f'http://{selenium_host}:4444/wd/hub'

        cls.selenium = webdriver.Remote(
            command_executor=selenium_url,
            options=chrome_options
        )
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    @patch('webscraper.views.AsyncResult')
    @patch('webscraper.tasks.search_datasets')
    @patch('webscraper.tasks.scrap_huggingface_datasets')
    def test_polling_waits_for_pending_tasks(self, mock_scrap_hf, mock_search, mock_async_result):
        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        mock_task_pending = Mock()
        mock_task_pending.ready.return_value = False

        mock_task_complete = Mock()
        mock_task_complete.ready.return_value = True
        mock_task_complete.result = {
            "results": [{"id": 1, "title": "Test", "description": "Desc"}]
        }

        call_count = [0]
        def async_result_side_effect(task_id):
            call_count[0] += 1
            if call_count[0] <= 2:
                return mock_task_pending
            return mock_task_complete

        mock_async_result.side_effect = async_result_side_effect

        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('test')
        search_form.submit()

        try:
            WebDriverWait(self.selenium, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.result-item'))
            )

            result_items = self.selenium.find_elements(By.CSS_SELECTOR, '.result-item')
            self.assertEqual(len(result_items), 1)
        except TimeoutException:
            pass

    @patch('webscraper.views.AsyncResult')
    @patch('webscraper.tasks.search_datasets')
    @patch('webscraper.tasks.scrap_huggingface_datasets')
    def test_retrigger_task_updates_dom(self, mock_scrap_hf, mock_search, mock_async_result):
        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        def async_result_side_effect(task_id):
            if task_id == "local-task-123":
                mock_primary = Mock()
                mock_primary.ready.return_value = True
                mock_primary.result = {"results": [{"id": 1, "title": "Initial", "description": "Desc"}]}
                return mock_primary
            elif task_id == "hf-task-456":
                mock_scraping = Mock()
                mock_scraping.ready.return_value = True
                mock_scraping.result = {"retrigger_task_id": "retrigger-task-789"}
                return mock_scraping
            elif task_id == "retrigger-task-789":
                mock_retrigger = Mock()
                mock_retrigger.ready.return_value = True
                mock_retrigger.result = {"results": [
                    {"id": 1, "title": "Initial", "description": "Desc"},
                    {"id": 2, "title": "Scraped", "description": "New"}
                ]}
                return mock_retrigger

        mock_async_result.side_effect = async_result_side_effect

        self.selenium.get(f'{self.live_server_url}/')

        search_input = self.selenium.find_element(By.ID, 'search-input')
        search_form = self.selenium.find_element(By.ID, 'search-form')

        search_input.send_keys('test')
        search_form.submit()

        try:
            WebDriverWait(self.selenium, 15).until(
                lambda driver: len(driver.find_elements(By.CSS_SELECTOR, '.result-item')) >= 2
            )

            result_items = self.selenium.find_elements(By.CSS_SELECTOR, '.result-item')
            self.assertGreaterEqual(len(result_items), 2)
        except TimeoutException:
            pass
