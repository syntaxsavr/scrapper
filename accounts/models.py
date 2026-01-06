import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta


def user_profile_image_path(instance, filename):
    """Generate file path for user profile images"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return os.path.join('profile_images', str(instance.user.id), filename)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=100, help_text="Your full name")
    profile_image = models.ImageField(
        upload_to=user_profile_image_path, 
        blank=True, 
        null=True,
        help_text="Upload a profile picture"
    )
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    date_of_birth = models.DateField(blank=True, null=True)
    last_username_change = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def can_change_username(self):
        """Check if user can change username (6-month rule)"""
        if not self.last_username_change:
            return True
        return timezone.now() > self.last_username_change + timedelta(days=180)

    @property
    def next_username_change_date(self):
        """Get the next date when username can be changed"""
        if not self.last_username_change:
            return timezone.now()
        return self.last_username_change + timedelta(days=180)

    @property
    def days_until_username_change(self):
        """Get number of days until username can be changed"""
        if self.can_change_username:
            return 0
        next_change = self.next_username_change_date
        return (next_change - timezone.now()).days

    class Meta:
        ordering = ['-created_at']


class PaymentMethod(models.Model):
    CARD_TYPES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('paypal', 'PayPal'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    cardholder_name = models.CharField(max_length=100)
    last_four_digits = models.CharField(max_length=4, help_text="Last 4 digits of card")
    expiry_month = models.IntegerField(blank=True, null=True)
    expiry_year = models.IntegerField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    billing_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.card_type.title()} ****{self.last_four_digits}"

    def save(self, *args, **kwargs):
        # Ensure only one primary payment method per user
        if self.is_primary:
            PaymentMethod.objects.filter(
                user=self.user, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class UsernameChangeHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='username_history')
    old_username = models.CharField(max_length=150)
    new_username = models.CharField(max_length=150)
    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = "Username change histories"

    def __str__(self):
        return f"{self.old_username} → {self.new_username}"
