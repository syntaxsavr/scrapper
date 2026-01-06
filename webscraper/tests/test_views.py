from django.test import TestCase
from django.urls import reverse
from webscraper.models import Dataset
from webscraper.tests.constants import OK, REDIRECT, NOT_FOUND
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

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