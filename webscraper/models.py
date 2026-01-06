from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinLengthValidator, MaxLengthValidator

class Log(models.Model):
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

class Dataset(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

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