from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinLengthValidator, MaxLengthValidator
import json  # for storing scrape results

class Log(models.Model):
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

class Dataset(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # HuggingFace metadata
    author = models.CharField(max_length=200, blank=True)  # dataset creator/owner
    tags = models.TextField(blank=True)  # comma-separated tags
    downloads = models.IntegerField(null=True, blank=True)  # number of downloads
    likes = models.IntegerField(null=True, blank=True)  # number of likes/favorites
    url = models.URLField(max_length=1000, blank=True)  # HuggingFace URL
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class UserProfile(models.Model):
    """Extended user profile with additional fields"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')  # link to user
    full_name = models.CharField(max_length=100)  # actual name not username
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)  # pfp
    bio = models.TextField(max_length=500, blank=True)  # about me section
    phone_number = models.CharField(max_length=20, blank=True)  # contact info
    date_of_birth = models.DateField(blank=True, null=True)  # bday
    
    # Username change tracking - prevent spam changes
    username_last_changed = models.DateTimeField(default=timezone.now)  # when last changed
    
    created_at = models.DateTimeField(auto_now_add=True)  # when made
    updated_at = models.DateTimeField(auto_now=True)  # last edit

    def __str__(self):
        return f"{self.user.username} - {self.full_name}"
    
    @property
    def can_change_username(self):
        """Check if user can change username (every 6 months)"""
        six_months_ago = timezone.now() - timedelta(days=180)  # 6 month cooldown
        return self.username_last_changed <= six_months_ago
    
    @property
    def days_until_username_change(self):
        """Calculate days until username can be changed"""
        if self.can_change_username:  # already can change
            return 0
        six_months_later = self.username_last_changed + timedelta(days=180)  # next allowed date
        days_left = (six_months_later - timezone.now()).days  # calc remaining
        return max(0, days_left)  # no negatives


class PaymentMethod(models.Model):
    """Mock payment method for user"""
    CARD_TYPES = [  # fake payment types for testing
        ('visa', 'Visa'),
        ('mastercard', 'MasterCard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('paypal', 'PayPal'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')  # owner
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)  # what kind of card
    cardholder_name = models.CharField(max_length=100)  # name on card
    last_four_digits = models.CharField(  # only store last 4 for security
        max_length=4, 
        validators=[MinLengthValidator(4), MaxLengthValidator(4)]
    )
    expiry_month = models.IntegerField()  # when expires
    expiry_year = models.IntegerField()   # year expires
    billing_address = models.TextField()  # where bills go
    is_primary = models.BooleanField(default=False)  # default payment method
    
    created_at = models.DateTimeField(auto_now_add=True)  # when added
    updated_at = models.DateTimeField(auto_now=True)      # last modified

    class Meta:
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.get_card_type_display()} ending in {self.last_four_digits}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary payment method per user - no duplicates
        if self.is_primary:
            PaymentMethod.objects.filter(user=self.user, is_primary=True).update(is_primary=False)  # remove other primaries
        super().save(*args, **kwargs)


class ScrapingProject(models.Model):
    """User's scraping projects - organize scraped data"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scraping_projects')  # owner
    name = models.CharField(max_length=200)  # project name
    description = models.TextField(blank=True)  # what this project is about
    
    # project settings
    is_favorite = models.BooleanField(default=False)  # star important projects
    color = models.CharField(max_length=7, default='#007bff')  # project color theme
    
    created_at = models.DateTimeField(auto_now_add=True)  # when made
    updated_at = models.DateTimeField(auto_now=True)  # last modified
    
    class Meta:
        ordering = ['-updated_at']  # newest first
        unique_together = ['user', 'name']  # no duplicate project names per user
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    @property 
    def scrape_count(self):
        """How many scrapes in this project"""
        return self.scrapes.count()  # count related scrapes
    
    @property
    def latest_scrape(self):
        """Most recent scrape in project"""
        return self.scrapes.first()  # first = newest due to ordering


class UserScrape(models.Model):
    """Individual scraping session by user"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'), 
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SCHEDULE_CHOICES = [
        ('none', 'No Schedule'),
        ('hourly', 'Every Hour'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scrapes')  # who scraped
    project = models.ForeignKey(ScrapingProject, on_delete=models.CASCADE, related_name='scrapes', null=True, blank=True)  # which project
    
    # scrape details
    query = models.CharField(max_length=500)  # what they searched for
    source = models.CharField(max_length=100, default='hugging_face')  # where scraped from
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # current state
    
    # celery task tracking for cancellation
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)  # track running task
    
    # scheduling for automatic reruns
    schedule_frequency = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='none')  # how often to rerun
    last_run_at = models.DateTimeField(null=True, blank=True)  # when last auto-run
    next_run_at = models.DateTimeField(null=True, blank=True)  # when next scheduled run
    is_scheduled_active = models.BooleanField(default=False)  # is scheduling enabled
    
    # results and stats
    results_count = models.IntegerField(default=0)  # how many results found
    results_data = models.JSONField(default=dict, blank=True)  # actual scraped data
    error_message = models.TextField(blank=True)  # if something went wrong
    
    # timing info
    started_at = models.DateTimeField(auto_now_add=True)  # when started
    completed_at = models.DateTimeField(null=True, blank=True)  # when finished
    duration_seconds = models.IntegerField(null=True, blank=True)  # how long it took
    
    # user organization
    is_bookmarked = models.BooleanField(default=False)  # saved for later
    notes = models.TextField(blank=True)  # user notes about this scrape
    tags = models.CharField(max_length=500, blank=True)  # comma separated tags
    
    class Meta:
        ordering = ['-started_at']  # newest first
    
    def __str__(self):
        return f"{self.user.username} - {self.query[:50]}"
    
    @property
    def duration_formatted(self):
        """Human readable duration"""
        if not self.duration_seconds:
            return "Unknown"
        
        minutes, seconds = divmod(self.duration_seconds, 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    
    @property
    def tag_list(self):
        """Convert comma separated tags to list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


class ScrapedDataItem(models.Model):
    """Individual item from a scrape session"""
    scrape = models.ForeignKey(UserScrape, on_delete=models.CASCADE, related_name='items')  # which scrape this belongs to
    
    # item details
    title = models.CharField(max_length=500)  # dataset title
    description = models.TextField(blank=True)  # dataset description
    url = models.URLField(max_length=1000)  # link to original
    
    # metadata
    downloads = models.IntegerField(null=True, blank=True)  # how many downloads
    likes = models.IntegerField(null=True, blank=True)  # how many likes
    author = models.CharField(max_length=200, blank=True)  # who made it
    tags = models.TextField(blank=True)  # dataset tags
    
    # user interaction
    is_starred = models.BooleanField(default=False)  # user marked as important
    user_notes = models.TextField(blank=True)  # user notes about this item
    
    created_at = models.DateTimeField(auto_now_add=True)  # when scraped
    
    def __str__(self):
        return f"{self.scrape.user.username} - {self.title[:50]}"
