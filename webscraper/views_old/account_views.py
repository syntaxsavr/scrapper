from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..models import UserProfile, PaymentMethod
from ..forms import UserProfileForm, UsernameChangeForm


@login_required
def profile_view(request):
    """User profile view"""
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.get_full_name() or request.user.username}
    )
    
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    
    context = {
        'profile': profile,
        'payment_methods': payment_methods,
        'can_change_username': profile.can_change_username,
        'days_until_username_change': profile.days_until_username_change
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    """Edit user profile"""
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.get_full_name() or request.user.username}
    )
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {'form': form, 'profile': profile}
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def change_username_view(request):
    """Change username with 6-month restriction"""
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.get_full_name() or request.user.username}
    )
    
    if not profile.can_change_username:
        messages.error(request, f'You can only change your username every 6 months. Please wait {profile.days_until_username_change} more days.')
        return redirect('profile')
    
    if request.method == 'POST':
        form = UsernameChangeForm(request.POST, user=request.user)
        if form.is_valid():
            new_username = form.cleaned_data['new_username']
            request.user.username = new_username
            request.user.save()
            
            profile.username_last_changed = timezone.now()
            profile.save()
            
            messages.success(request, f'Username successfully changed to {new_username}')
            return redirect('profile')
    else:
        form = UsernameChangeForm(user=request.user)
    
    context = {'form': form, 'profile': profile}
    return render(request, 'accounts/change_username.html', context)


@login_required
def profile_api(request):
    """API endpoint to get profile data for dropdown menu."""
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': request.user.get_full_name() or request.user.username}
    )
    
    profile_image_url = None
    if profile.profile_image:
        profile_image_url = profile.profile_image.url
    
    return JsonResponse({
        'username': request.user.username,
        'full_name': profile.full_name,
        'email': request.user.email,
        'profile_image': profile_image_url,
        'can_change_username': profile.can_change_username,
        'days_until_username_change': profile.days_until_username_change
    })
