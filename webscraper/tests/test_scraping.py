from django.test import TestCase
from unittest.mock import patch, MagicMock
from webscraper.models import Dataset
from webscraper.tasks import scrap_huggingface_datasets


class ScrapHuggingfaceDatasetsTests(TestCase):
    @patch('webscraper.tasks.search_datasets.delay')
    @patch('webscraper.tasks.fetch_huggingface_datasets')
    def test_creates_new_datasets_from_scraped_items(self, mock_fetch, mock_search_delay):
        mock_fetch.return_value = [
            {"title": "dataset1", "description": "description1"},
            {"title": "dataset2", "description": "description2"},
        ]
        mock_search_delay.return_value = MagicMock(id="task-123")

        scrap_huggingface_datasets("machine learning")

        self.assertEqual(Dataset.objects.count(), 2)
        self.assertTrue(Dataset.objects.filter(title="dataset1", description="description1").exists())
        self.assertTrue(Dataset.objects.filter(title="dataset2", description="description2").exists())

    @patch('webscraper.tasks.search_datasets.delay')
    @patch('webscraper.tasks.fetch_huggingface_datasets')
    def test_skips_existing_datasets(self, mock_fetch, mock_search_delay):
        Dataset.objects.create(title="existing_dataset", description="old description")

        mock_fetch.return_value = [
            {"title": "existing_dataset", "description": "new description"},
            {"title": "new_dataset", "description": "description"},
        ]
        mock_search_delay.return_value = MagicMock(id="task-123")

        scrap_huggingface_datasets("test query")

        self.assertEqual(Dataset.objects.count(), 2)
        existing = Dataset.objects.get(title="existing_dataset")
        self.assertEqual(existing.description, "old description")
    @patch('webscraper.tasks.fetch_huggingface_datasets')
    def test_calls_fetch_with_correct_parameters(self, mock_fetch, mock_search_delay):
        mock_fetch.return_value = []
        mock_search_delay.return_value = MagicMock(id="task-123")

        scrap_huggingface_datasets("test query")

        mock_fetch.assert_called_once_with(query="test query", limit=50)

    @patch('webscraper.tasks.search_datasets.delay')
    @patch('webscraper.tasks.fetch_huggingface_datasets')
    def test_triggers_search_task_with_query(self, mock_fetch, mock_search_delay):
        mock_fetch.return_value = [{"title": "dataset1", "description": "desc1"}]
        mock_search_delay.return_value = MagicMock(id="task-456")

        scrap_huggingface_datasets("python datasets")

        mock_search_delay.assert_called_once_with("python datasets")

    @patch('webscraper.tasks.search_datasets.delay')
    @patch('webscraper.tasks.fetch_huggingface_datasets')
    def test_returns_retrigger_task_id(self, mock_fetch, mock_search_delay):
        mock_fetch.return_value = []
        mock_task = MagicMock(id="task-789")
        mock_search_delay.return_value = mock_task

        result = scrap_huggingface_datasets("test")

        self.assertIsInstance(result, dict)
        self.assertIn("retrigger_task_id", result)
        self.assertEqual(result["retrigger_task_id"], "task-789")

    @patch('webscraper.tasks.search_datasets.delay')
    @patch('webscraper.tasks.fetch_huggingface_datasets')
    def test_handles_empty_scrape_results(self, mock_fetch, mock_search_delay):
        mock_fetch.return_value = []
        mock_search_delay.return_value = MagicMock(id="task-000")

        result = scrap_huggingface_datasets("nonexistent query")

        self.assertEqual(Dataset.objects.count(), 0)
        self.assertIn("retrigger_task_id", result)
        mock_search_delay.assert_called_once()
