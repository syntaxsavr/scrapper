
def user_profile(request):
    """
    context processor to add user profile to all templates
    makes the dropdown work everywhere without manual passing
    """
    context = {}
    if request.user.is_authenticated:  # only for logged-in users
        from .models import UserProfile  # get our profile model
        try:
            # use get_or_create to avoid DoesNotExist issues
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'full_name': request.user.get_full_name() or request.user.username}
            )
        except Exception as e:
            # fallback in case something goes wrong
            profile = None
        context['user_profile'] = profile  # add to context
    return context
