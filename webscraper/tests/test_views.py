from django.test import TestCase
from django.urls import reverse
from webscraper.models import Dataset
from webscraper.tests.constants import OK, REDIRECT, NOT_FOUND, BAD_REQUEST
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from unittest.mock import patch, Mock

class ViewTests(TestCase):
    def test_home_view_renders(self):
        url = reverse("home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, "home.html")

    def test_home_view_shows_login_signup(self):
        url = reverse("home")
        response = self.client.get(url)

        self.assertContains(response, "Login")
        self.assertContains(response, "Sign Up")
        self.assertNotContains(response, "Logout")

    def test_detailed_view_valid_id(self):
        dataset = Dataset.objects.create(
            title="Test Dataset",
            description="Test description"
        )

        url = reverse("detailed_view", kwargs={"id": dataset.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, "detailed_view.html")
        self.assertEqual(response.context["dataset"], dataset)

    def test_detailed_view_invalid_id(self):
        dataset = Dataset.objects.create(
            title="Test Dataset",
            description="Test description"
        )

        invalid_id = dataset.id + 1

        url = reverse("detailed_view", kwargs={"id": invalid_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, NOT_FOUND)

    def test_detailed_view_displays_dataset_fields(self):
        dataset = Dataset.objects.create(title="Test Dataset", description="")

        url = reverse("detailed_view", kwargs={"id": dataset.id})
        response = self.client.get(url)

        self.assertContains(response, "Test Dataset")
        self.assertNotContains(response, "Description:")

    def test_login_get_renders_form(self):
        url = reverse("login")
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)
        self.assertIn("form", response.context)

    def test_login_valid(self):
        User.objects.create_user(username="alice", password="password123")

        url = reverse("login")
        response = self.client.post(url, {
            "username": "alice",
            "password": "password123",
        })

        self.assertEqual(response.status_code, REDIRECT)
        self.assertRedirects(response, reverse("home"))

        response2 = self.client.get(reverse("home"))
        self.assertTrue(response2.wsgi_request.user.is_authenticated)
        self.assertEqual(response2.wsgi_request.user.username, "alice")

    def test_login_invalid(self):
        User.objects.create_user(username="alice", password="password123")

        url = reverse("login")
        response = self.client.post(url, {
            "username": "alice",
            "password": "wrongpassword"
        })

        self.assertEqual(response.status_code, OK)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_redirects_if_authenticated(self):
        User.objects.create_user(username="alice", password="password123")
        self.client.login(username="alice", password="password123")

        url = reverse("login")
        response = self.client.get(url)

        self.assertEqual(response.status_code, REDIRECT)
        self.assertRedirects(response, reverse("home"))

    def test_signup_redirects_if_user_is_authenticated(self):
        User.objects.create_user(username="alice", password="password123")
        self.client.login(username="alice", password="password123")

        url = reverse("signup")
        response = self.client.get(url)

        self.assertEqual(response.status_code, REDIRECT)
        self.assertRedirects(response, reverse("home"))

    def test_signup_get_renders_empty_usercreationform(self):
        url = reverse("signup")
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, "signup.html")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], UserCreationForm)

    def test_signup_post_valid(self):
        url = reverse("signup")
        response = self.client.post(url, {
            "username": "alice",
            "password1": "password123",
            "password2": "password123",
        })

        self.assertEqual(response.status_code, REDIRECT)
        self.assertRedirects(response, reverse("home"))

        self.assertTrue(User.objects.filter(username="alice").exists())

        response2 = self.client.get(reverse("home"))
        self.assertTrue(response2.wsgi_request.user.is_authenticated)
        self.assertEqual(response2.wsgi_request.user.username, "alice")

    def test_signup_post_invalid(self):
        url = reverse("signup")
        response = self.client.post(url, {
            "username": "alice",
            "password1": "password123",
            "password2": "differentpassword",
        })

        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, "signup.html")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], UserCreationForm)
        self.assertFalse(response.context["form"].is_valid())

    def test_signup_password_mismatch(self):
        url = reverse("signup")

        response = self.client.post(url, {
            "username": "alice",
            "password1": "password123",
            "password2": "differentpassword",
        })

        self.assertEqual(response.status_code, OK)
        self.assertFalse(User.objects.filter(username="alice").exists())

    def test_signup_duplicate_username(self):
        User.objects.create_user(username="alice", password="password123")

        url = reverse("signup")
        response = self.client.post(url, {
            "username": "alice",
            "password1": "password123",
            "password2": "password123",
        })

        self.assertEqual(response.status_code, OK)
        self.assertEqual(User.objects.filter(username="alice").count(), 1)

    @patch("webscraper.views.search_datasets")
    @patch("webscraper.views.scrap_huggingface_datasets")
    def test_api_search_valid_query(self, mock_scrap_hf, mock_search):
        mock_local_task = Mock()
        mock_local_task.id = "local-task-123"
        mock_search.delay.return_value = mock_local_task

        mock_hf_task = Mock()
        mock_hf_task.id = "hf-task-456"
        mock_scrap_hf.delay.return_value = mock_hf_task

        url = reverse("api_search")
        response = self.client.get(url, {"q": "machine learning"})

        self.assertEqual(response.status_code, OK)

        data = response.json()
        self.assertIn("task_ids", data)
        self.assertEqual(len(data["task_ids"]), 2)
        self.assertIn("local-task-123", data["task_ids"])
        self.assertIn("hf-task-456", data["task_ids"])

        mock_search.delay.assert_called_once_with("machine learning")
        mock_scrap_hf.delay.assert_called_once_with("machine learning")

    @patch("webscraper.views.search_datasets")
    @patch("webscraper.views.scrap_huggingface_datasets")
    def test_api_search_empty_query(self, mock_scrap_hf, mock_search):
        url = reverse("api_search")
        response = self.client.get(url, {"q": ""})

        self.assertEqual(response.status_code, BAD_REQUEST)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "No query provided")

        mock_search.delay.assert_not_called()
        mock_scrap_hf.delay.assert_not_called()

    @patch("webscraper.views.search_datasets")
    @patch("webscraper.views.scrap_huggingface_datasets")
    def test_api_search_no_query_parameter(self, mock_scrap_hf, mock_search):
        url = reverse("api_search")
        response = self.client.get(url)

        self.assertEqual(response.status_code, BAD_REQUEST)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "No query provided")

        mock_search.delay.assert_not_called()
        mock_scrap_hf.delay.assert_not_called()

    @patch("webscraper.views.AsyncResult")
    def test_api_task_status_completed_with_results(self, mock_async_result):
        mock_task = Mock()
        mock_task.ready.return_value = True
        mock_task.result = {
            "results": [
                {"id": 1, "title": "Dataset 1", "description": "Desc 1"},
                {"id": 2, "title": "Dataset 2", "description": "Desc 2"},
                {"id": 3, "title": "Dataset 3", "description": "Desc 3"}
            ]
        }
        mock_async_result.return_value = mock_task

        url = reverse("api_task_status", kwargs={"task_id": "test-task-123"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)

        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(data["results"][0]["title"], "Dataset 1")

        mock_async_result.assert_called_once_with("test-task-123")

    @patch("webscraper.views.AsyncResult")
    def test_api_task_status_completed_with_retrigger(self, mock_async_result):
        mock_task = Mock()
        mock_task.ready.return_value = True
        mock_task.result = {
            "retrigger_task_id": "retrigger-task-789"
        }
        mock_async_result.return_value = mock_task

        url = reverse("api_task_status", kwargs={"task_id": "test-task-456"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)

        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["retrigger_task_id"], "retrigger-task-789")
        self.assertNotIn("results", data)

        mock_async_result.assert_called_once_with("test-task-456")

    @patch("webscraper.views.AsyncResult")
    def test_api_task_status_pending(self, mock_async_result):
        mock_task = Mock()
        mock_task.ready.return_value = False
        mock_async_result.return_value = mock_task

        url = reverse("api_task_status", kwargs={"task_id": "pending-task-999"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)

        data = response.json()
        self.assertEqual(data["status"], "pending")
        self.assertNotIn("results", data)
        self.assertNotIn("retrigger_task_id", data)

        mock_async_result.assert_called_once_with("pending-task-999")

    @patch("webscraper.views.AsyncResult")
    def test_api_task_status_completed_empty_results(self, mock_async_result):
        mock_task = Mock()
        mock_task.ready.return_value = True
        mock_task.result = {
            "results": []
        }
        mock_async_result.return_value = mock_task

        url = reverse("api_task_status", kwargs={"task_id": "empty-task-111"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)

        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["results"], [])

        mock_async_result.assert_called_once_with("empty-task-111")