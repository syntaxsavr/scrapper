from django.test import TestCase
from django.urls import reverse
from webscraper.models import Dataset
from webscraper.tests.constants import OK, REDIRECT, NOT_FOUND
from django.contrib.auth.models import User

class ViewTests(TestCase):
    def test_home_view_renders(self):
        url = reverse("home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, "home.html")

    def test_home_shows_login_signup_when_anonymous(self):
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
        dataset = Dataset.objects.create(title="SQuAD", description="")

        url = reverse("detailed_view", kwargs={"id": dataset.id})
        response = self.client.get(url)

        self.assertContains(response, "SQuAD")
        self.assertNotContains(response, "Description:")

    def test_login_get_renders_form_for_anonymous(self):
        url = reverse("login")
        response = self.client.get(url)

        self.assertEqual(response.status_code, OK)
        self.assertIn("form", response.context)

    def test_login_redirects_if_authenticated(self):
        user = User.objects.create_user(
            username="alice",
            password="password123"
        )
        self.client.login(username="alice", password="password123")

        url = reverse("login")
        response = self.client.get(url)

        self.assertEqual(response.status_code, REDIRECT)
        self.assertRedirects(response, reverse("home"))

    def test_login_invalid_credentials_does_not_authenticate(self):
        User.objects.create_user(username="alice", password="password123")

        url = reverse("login")
        response = self.client.post(url, {
            "username": "alice",
            "password": "wrongpassword"
        })

        self.assertEqual(response.status_code, OK)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_signup_password_mismatch_does_not_create_user(self):
        url = reverse("signup")

        response = self.client.post(url, {
            "username": "bob",
            "password1": "password12345",
            "password2": "differentpassword",
        })

        self.assertEqual(response.status_code, OK)
        self.assertFalse(User.objects.filter(username="bob").exists())

    def test_signup_duplicate_username_fails(self):
        User.objects.create_user(username="bob", password="password123")

        url = reverse("signup")
        response = self.client.post(url, {
            "username": "bob",
            "password1": "password12345",
            "password2": "password12345",
        })

        self.assertEqual(response.status_code, OK)
        self.assertEqual(User.objects.filter(username="bob").count(), 1)