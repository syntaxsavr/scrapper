from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import UserProfile, PaymentMethod, UsernameChangeHistory
from .forms import CustomUserCreationForm, UserProfileForm, UsernameChangeForm, PaymentMethodForm


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def signup_view(request):
    """Enhanced signup view with full name"""
    if request.user.is_authenticated:
        return redirect('profile')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.profile.full_name}! Your account has been created.')
            return redirect('profile')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def profile_view(request):
    """User profile dashboard"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    payment_methods = PaymentMethod.objects.filter(user=request.user, is_active=True)
    
    context = {
        'profile': profile,
        'payment_methods': payment_methods,
        'can_change_username': profile.can_change_username,
        'days_until_username_change': profile.days_until_username_change if not profile.can_change_username else 0
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    """Edit user profile information"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'accounts/edit_profile.html', {'form': form, 'profile': profile})


@login_required
def change_username_view(request):
    """Change username with 6-month restriction"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UsernameChangeForm(request.POST, user=request.user)
        if form.is_valid():
            old_username = request.user.username
            new_username = form.cleaned_data['new_username']
            
            # Save username change history
            UsernameChangeHistory.objects.create(
                user=request.user,
                old_username=old_username,
                new_username=new_username,
                ip_address=get_client_ip(request)
            )
            
            # Update username and profile
            request.user.username = new_username
            request.user.save()
            
            profile.last_username_change = timezone.now()
            profile.save()
            
            messages.success(request, f'Username successfully changed to "{new_username}"!')
            return redirect('profile')
    else:
        form = UsernameChangeForm(user=request.user)
    
    context = {
        'form': form,
        'profile': profile,
        'can_change_username': profile.can_change_username,
        'days_until_change': profile.days_until_username_change
    }
    return render(request, 'accounts/change_username.html', context)


@login_required
def payment_methods_view(request):
    """View and manage payment methods"""
    payment_methods = PaymentMethod.objects.filter(user=request.user, is_active=True)
    return render(request, 'accounts/payment_methods.html', {'payment_methods': payment_methods})


@login_required
def add_payment_method_view(request):
    """Add new payment method"""
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.user = request.user
            payment_method.save()
            messages.success(request, 'Payment method added successfully!')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'accounts/add_payment_method.html', {'form': form})


@login_required
def edit_payment_method_view(request, payment_id):
    """Edit existing payment method"""
    payment_method = get_object_or_404(
        PaymentMethod, 
        id=payment_id, 
        user=request.user, 
        is_active=True
    )
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=payment_method)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment method updated successfully!')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm(instance=payment_method)
    
    return render(request, 'accounts/edit_payment_method.html', {
        'form': form, 
        'payment_method': payment_method
    })


@login_required
@require_POST
def delete_payment_method_view(request, payment_id):
    """Delete (deactivate) payment method"""
    payment_method = get_object_or_404(
        PaymentMethod, 
        id=payment_id, 
        user=request.user, 
        is_active=True
    )
    
    # Don't allow deletion of primary payment method if it's the only one
    active_methods = PaymentMethod.objects.filter(user=request.user, is_active=True).count()
    
    if payment_method.is_primary and active_methods > 1:
        # Make another payment method primary
        next_method = PaymentMethod.objects.filter(
            user=request.user, 
            is_active=True
        ).exclude(id=payment_id).first()
        next_method.is_primary = True
        next_method.save()
    
    payment_method.is_active = False
    payment_method.save()
    
    messages.success(request, 'Payment method removed successfully!')
    return redirect('payment_methods')


@login_required
@require_POST
def set_primary_payment_method_view(request, payment_id):
    """Set payment method as primary"""
    payment_method = get_object_or_404(
        PaymentMethod, 
        id=payment_id, 
        user=request.user, 
        is_active=True
    )
    
    # Remove primary status from other methods
    PaymentMethod.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    
    # Set this method as primary
    payment_method.is_primary = True
    payment_method.save()
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'success'})
    
    messages.success(request, 'Primary payment method updated!')
    return redirect('payment_methods')


@login_required
def username_availability_api(request):
    """API endpoint to check username availability"""
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'available': False, 'message': 'Username is required'})
    
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters'})
    
    # Check if username exists (excluding current user)
    exists = User.objects.filter(username=username).exclude(pk=request.user.pk).exists()
    
    if exists:
        return JsonResponse({'available': False, 'message': 'Username is already taken'})
    
    return JsonResponse({'available': True, 'message': 'Username is available'})
