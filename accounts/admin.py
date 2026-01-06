from django.contrib import admin
from .models import UserProfile, PaymentMethod, UsernameChangeHistory

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'last_username_change', 'created_at')
    search_fields = ('user__username', 'full_name', 'user__email')
    list_filter = ('created_at', 'last_username_change')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_type', 'last_four_digits', 'is_primary', 'is_active', 'created_at')
    search_fields = ('user__username', 'cardholder_name')
    list_filter = ('card_type', 'is_primary', 'is_active', 'created_at')

@admin.register(UsernameChangeHistory)
class UsernameChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'old_username', 'new_username', 'changed_at')
    search_fields = ('user__username', 'old_username', 'new_username')
    list_filter = ('changed_at',)
    readonly_fields = ('changed_at',)
