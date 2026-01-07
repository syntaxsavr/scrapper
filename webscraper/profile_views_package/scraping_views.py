from django.test import TestCase
from django.urls import reverse
from webscraper.models import Dataset
from webscraper.tests.constants import OK, REDIRECT, NOT_FOUND
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from webscraper.models import UserProfile, PaymentMethod, ScrapingProject, UserScrape, ScrapedDataItem
from django.utils import timezone
from datetime import timedelta
import json

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
        self.assertTemplateUsed(response, "accounts/signup.html")
        self.assertIn("form", response.context)

    def test_signup_post_valid(self):
        url = reverse("signup")
        response = self.client.post(url, {
            "username": "alice",
            "full_name": "Alice Smith",
            "email": "alice@example.com",
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
            "full_name": "Alice Smith",
            "email": "alice@example.com",
            "password1": "password123",
            "password2": "differentpassword",
        })

        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, "accounts/signup.html")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    def test_signup_password_mismatch(self):
        url = reverse("signup")

        response = self.client.post(url, {
            "username": "alice",
            "full_name": "Alice Smith",
            "email": "alice@example.com",
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
            "full_name": "Alice Smith",
            "email": "newalice@example.com",
            "password1": "password123",
            "password2": "password123",
        })

        self.assertEqual(response.status_code, OK)
        self.assertEqual(User.objects.filter(username="alice").count(), 1)


class AccountViewsTests(TestCase):
    """
    Tests for account_views in profile_views_package
    This is for all the stuff inside the "profile_views_package folder
    """
    
    def setUp(self):
        """Create test user and profile"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name='Test User'
        )
    
    def test_profile_view_requires_login(self):
        """Profile view should redirect unauthenticated users"""
        url = reverse('profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertIn('/login/', response.url)
    
    def test_profile_view_authenticated(self):
        """Profile view should render for authenticated users"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertEqual(response.context['profile'], self.profile)
    
    def test_profile_view_creates_profile_if_not_exists(self):
        """Profile view should auto-create profile if missing"""
        user2 = User.objects.create_user(username='newuser', password='pass123')
        self.client.login(username='newuser', password='pass123')
        
        url = reverse('profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTrue(UserProfile.objects.filter(user=user2).exists())
    
    def test_edit_profile_view_get(self):
        """Edit profile view should render form"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('edit_profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, 'accounts/edit_profile.html')
        self.assertIn('form', response.context)
    
    def test_edit_profile_view_post_valid(self):
        """Edit profile should save changes"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('edit_profile')
        
        response = self.client.post(url, {
            'full_name': 'Updated Name',
            'bio': 'New bio text',
            'phone_number': '1234567890'
        })
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertRedirects(response, reverse('profile'))
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, 'Updated Name')
        self.assertEqual(self.profile.bio, 'New bio text')
    
    def test_change_username_view_not_allowed(self):
        """Change username should reject if within 6-month period"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('change_username')
        
        response = self.client.post(url, {
            'new_username': 'newusername',
            'confirm_username': 'newusername'
        })
        
        # Should redirect back to profile with error message
        self.assertEqual(response.status_code, REDIRECT)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')  # Username unchanged
    
    def test_change_username_view_allowed(self):
        """Change username should work after 6 months"""
        self.client.login(username='testuser', password='testpass123')
        
        # Set username_last_changed to 7 months ago
        self.profile.username_last_changed = timezone.now() - timedelta(days=210)
        self.profile.save()
        
        url = reverse('change_username')
        response = self.client.post(url, {
            'new_username': 'newusername',
            'confirm_username': 'newusername'
        })
        
        self.assertEqual(response.status_code, REDIRECT)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')
    
    def test_profile_api_returns_json(self):
        """Profile API should return JSON data"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('profile_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        data = json.loads(response.content)
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['full_name'], 'Test User')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertIn('can_change_username', data)


class PaymentViewsTests(TestCase):
    """Tests for payment_views in profile_views_package"""
    
    def setUp(self):
        """Create test user and payment method"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.payment = PaymentMethod.objects.create(
            user=self.user,
            card_type='visa',
            cardholder_name='Test User',
            last_four_digits='1234',
            expiry_month=12,
            expiry_year=2025,
            billing_address='123 Test St'
        )
    
    def test_payment_methods_view_requires_login(self):
        """Payment methods view should require authentication"""
        url = reverse('payment_methods')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertIn('/login/', response.url)
    
    def test_payment_methods_view_shows_user_cards(self):
        """Payment methods view should show only user's cards"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create card for different user
        other_user = User.objects.create_user(username='other', password='pass')
        PaymentMethod.objects.create(
            user=other_user,
            card_type='mastercard',
            cardholder_name='Other User',
            last_four_digits='5678',
            expiry_month=10,
            expiry_year=2026,
            billing_address='456 Other St'
        )
        
        url = reverse('payment_methods')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertEqual(len(response.context['payment_methods']), 1)
        self.assertEqual(response.context['payment_methods'][0].user, self.user)
    
    def test_add_payment_method_view_post_valid(self):
        """Add payment method should create new card"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('add_payment_method')
        
        response = self.client.post(url, {
            'card_type': 'mastercard',
            'cardholder_name': 'Test User',
            'last_four_digits': '9999',
            'expiry_month': 6,
            'expiry_year': 2026,
            'billing_address': '789 New St'
        })
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertEqual(PaymentMethod.objects.filter(user=self.user).count(), 2)
    
    def test_edit_payment_method_view_unauthorized(self):
        """Edit payment should fail for non-owner"""
        other_user = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')
        
        url = reverse('edit_payment_method', kwargs={'payment_id': self.payment.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, NOT_FOUND)
    
    def test_edit_payment_method_view_authorized(self):
        """Edit payment should work for owner"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('edit_payment_method', kwargs={'payment_id': self.payment.id})
        
        response = self.client.post(url, {
            'card_type': 'visa',
            'cardholder_name': 'Updated Name',
            'last_four_digits': '1234',
            'expiry_month': 12,
            'expiry_year': 2025,
            'billing_address': '123 Test St'
        })
        
        self.assertEqual(response.status_code, REDIRECT)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.cardholder_name, 'Updated Name')
    
    def test_delete_payment_method_view_post(self):
        """Delete payment should remove card"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('delete_payment_method', kwargs={'payment_id': self.payment.id})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertFalse(PaymentMethod.objects.filter(id=self.payment.id).exists())
    
    def test_delete_payment_method_view_get(self):
        """Delete payment GET should show confirmation page"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('delete_payment_method', kwargs={'payment_id': self.payment.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, 'accounts/delete_payment_method.html')


class ScrapingViewsTests(TestCase):
    """Tests for scraping_views in profile_views_package"""
    
    def setUp(self):
        """Create test user, project, scrape, and items"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = ScrapingProject.objects.create(
            user=self.user,
            name='Test Project',
            description='Test description'
        )
        self.scrape = UserScrape.objects.create(
            user=self.user,
            project=self.project,
            query='test query',
            status='completed',
            results_count=5
        )
        self.item = ScrapedDataItem.objects.create(
            scrape=self.scrape,
            title='Test Item',
            description='Test description',
            url='https://example.com'
        )
    
    def test_dashboard_view_requires_login(self):
        """Dashboard should require authentication"""
        url = reverse('dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, REDIRECT)
    
    def test_dashboard_view_shows_stats(self):
        """Dashboard should display user stats"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, 'scraping/dashboard.html')
        self.assertEqual(response.context['total_scrapes'], 1)
        self.assertEqual(response.context['total_projects'], 1)
        self.assertEqual(response.context['total_results'], 1)
    
    def test_projects_view_lists_user_projects(self):
        """Projects view should list only user's projects"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create project for different user
        other_user = User.objects.create_user(username='other', password='pass')
        ScrapingProject.objects.create(
            user=other_user,
            name='Other Project'
        )
        
        url = reverse('projects')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertEqual(len(response.context['projects']), 1)
        self.assertEqual(response.context['projects'][0].user, self.user)
    
    def test_create_project_view_post_valid(self):
        """Create project should add new project"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('create_project')
        
        response = self.client.post(url, {
            'name': 'New Project',
            'description': 'New description',
            'color': '#ff0000'
        })
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertEqual(ScrapingProject.objects.filter(user=self.user).count(), 2)
    
    def test_project_detail_view_shows_scrapes(self):
        """Project detail should show project's scrapes"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('project_detail', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, 'scraping/project_detail.html')
        self.assertEqual(response.context['project'], self.project)
        self.assertIn(self.scrape, response.context['scrapes'])
    
    def test_edit_project_view_unauthorized(self):
        """Edit project should fail for non-owner"""
        other_user = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')
        
        url = reverse('edit_project', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, NOT_FOUND)
    
    def test_scrapes_view_filters_by_status(self):
        """Scrapes view should filter by status"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create scrape with different status
        UserScrape.objects.create(
            user=self.user,
            query='failed query',
            status='failed'
        )
        
        url = reverse('scrapes') + '?status=completed'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        scrapes = response.context['scrapes']
        self.assertEqual(len(scrapes), 1)
        self.assertEqual(scrapes[0].status, 'completed')
    
    def test_scrapes_view_filters_by_project(self):
        """Scrapes view should filter by project"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create scrape without project
        UserScrape.objects.create(
            user=self.user,
            query='no project query'
        )
        
        url = reverse('scrapes') + f'?project={self.project.id}'
        response = self.client.get(url)
        
        scrapes = response.context['scrapes']
        self.assertEqual(len(scrapes), 1)
        self.assertEqual(scrapes[0].project, self.project)
    
    def test_scrape_detail_view_shows_items(self):
        """Scrape detail should display scraped items"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('scrape_detail', kwargs={'scrape_id': self.scrape.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        self.assertTemplateUsed(response, 'scraping/scrape_detail.html')
        self.assertEqual(response.context['scrape'], self.scrape)
        self.assertIn(self.item, response.context['items'])
    
    def test_edit_scrape_view_updates_scrape(self):
        """Edit scrape should update scrape details"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('edit_scrape', kwargs={'scrape_id': self.scrape.id})
        
        response = self.client.post(url, {
            'notes': 'Updated notes',
            'tags': 'tag1, tag2',
            'is_bookmarked': True
        })
        
        self.assertEqual(response.status_code, REDIRECT)
        self.scrape.refresh_from_db()
        self.assertEqual(self.scrape.notes, 'Updated notes')
    
    def test_toggle_bookmark_api_requires_post(self):
        """Toggle bookmark API should require POST"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('toggle_bookmark', kwargs={'scrape_id': self.scrape.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 405)
    
    def test_toggle_bookmark_api_toggles_status(self):
        """Toggle bookmark API should toggle bookmark status"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('toggle_bookmark', kwargs={'scrape_id': self.scrape.id})
        
        initial_status = self.scrape.is_bookmarked
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, OK)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        self.scrape.refresh_from_db()
        self.assertEqual(self.scrape.is_bookmarked, not initial_status)
    
    def test_toggle_star_api_toggles_item_star(self):
        """Toggle star API should toggle item star status"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('toggle_star', kwargs={'item_id': self.item.id})
        
        initial_status = self.item.is_starred
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, OK)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        self.item.refresh_from_db()
        self.assertEqual(self.item.is_starred, not initial_status)
    
    def test_add_scrape_to_project_api(self):
        """Add scrape to project API should assign project"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create scrape without project
        scrape2 = UserScrape.objects.create(
            user=self.user,
            query='no project'
        )
        
        url = reverse('add_scrape_to_project', kwargs={'scrape_id': scrape2.id})
        response = self.client.post(url, {'project_id': self.project.id})
        
        self.assertEqual(response.status_code, OK)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        scrape2.refresh_from_db()
        self.assertEqual(scrape2.project, self.project)
    
    def test_delete_scrape_view_deletes_scrape(self):
        """Delete scrape should remove scrape and items"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('delete_scrape', kwargs={'scrape_id': self.scrape.id})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, REDIRECT)
        self.assertFalse(UserScrape.objects.filter(id=self.scrape.id).exists())
        self.assertFalse(ScrapedDataItem.objects.filter(id=self.item.id).exists())
    
    def test_stats_api_view_returns_json(self):
        """Stats API should return JSON data for charts"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('scraping_stats_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, OK)
        data = json.loads(response.content)
        
        self.assertIn('monthly_stats', data)
        self.assertIn('status_distribution', data)
        self.assertIn('project_stats', data)