from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/change-username/', views.change_username_view, name='change_username'),
    
    # Payment methods
    path('payment-methods/', views.payment_methods_view, name='payment_methods'),
    path('payment-methods/add/', views.add_payment_method_view, name='add_payment_method'),
    path('payment-methods/<int:payment_id>/edit/', views.edit_payment_method_view, name='edit_payment_method'),
    path('payment-methods/<int:payment_id>/delete/', views.delete_payment_method_view, name='delete_payment_method'),
    path('payment-methods/<int:payment_id>/set-primary/', views.set_primary_payment_method_view, name='set_primary_payment_method'),
    
    # API endpoints
    path('api/username-availability/', views.username_availability_api, name='username_availability'),
]
