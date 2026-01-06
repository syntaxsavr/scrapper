from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile, PaymentMethod, ScrapingProject, UserScrape, ScrapedDataItem  # add new models, ScrapingProject, UserScrape, ScrapedDataItem


class CustomUserCreationForm(UserCreationForm):
    """Enhanced signup form with full name and email"""
    full_name = forms.CharField(  # real name field for signup
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    email = forms.EmailField(  # email is required for account
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'full_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to existing fields - make em look nice
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():  # check if email already used
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create user profile - auto make one when user signs up
            UserProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name']
            )
        return user


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    class Meta:
        model = UserProfile
        fields = ['full_name', 'profile_image', 'bio', 'phone_number', 'date_of_birth']
        widgets = {  # styling for all fields
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'  # html5 date picker
            }),
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'  # only images
            }),
        }


class UsernameChangeForm(forms.Form):
    """Form for changing username with validation"""
    new_username = forms.CharField(  # new username field
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new username'
        })
    )
    confirm_username = forms.CharField(  # confirm to prevent typos
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new username'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user  # need current user for validation
        super().__init__(*args, **kwargs)

    def clean_new_username(self):
        new_username = self.cleaned_data.get('new_username')
        
        # Check if username is already taken - no duplicates
        if User.objects.filter(username=new_username).exclude(pk=self.user.pk).exists():
            raise ValidationError("This username is already taken.")
        
        # Check if user can change username (6-month rule) - prevent spam
        if not self.user.profile.can_change_username:
            days_left = self.user.profile.days_until_username_change
            raise ValidationError(
                f"You can only change your username every 6 months. "
                f"Please wait {days_left} more days."
            )
        
        return new_username

    def clean(self):
        cleaned_data = super().clean()
        new_username = cleaned_data.get('new_username')
        confirm_username = cleaned_data.get('confirm_username')

        if new_username and confirm_username and new_username != confirm_username:  # make sure they match
            raise ValidationError("Usernames don't match.")

        return cleaned_data


class PaymentMethodForm(forms.ModelForm):
    """Form for adding/editing payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = [  # all payment fields
            'card_type', 'cardholder_name', 'last_four_digits', 
            'expiry_month', 'expiry_year', 'billing_address', 'is_primary'
        ]
        widgets = {  # make em look nice
            'card_type': forms.Select(attrs={'class': 'form-control'}),
            'cardholder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name as on card'
            }),
            'last_four_digits': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234',
                'maxlength': '4'  # only 4 digits for security
            }),
            'expiry_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 12,
                'placeholder': 'MM'
            }),
            'expiry_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2024,  # cant expire in past
                'max': 2040,
                'placeholder': 'YYYY'
            }),
            'billing_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter billing address'
            }),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # default payment
        }

    def clean_last_four_digits(self):
        last_four = self.cleaned_data.get('last_four_digits')
        if not last_four.isdigit():  # numbers only
            raise ValidationError("Last four digits must be numbers only.")
        if len(last_four) != 4:  # exactly 4 digits
            raise ValidationError("Must be exactly 4 digits.")
        return last_four


class ScrapingProjectForm(forms.ModelForm):
    """Form for creating/editing scraping projects"""
    
    class Meta:
        model = ScrapingProject  # need to import this
        fields = ['name', 'description', 'color', 'is_favorite']
        widgets = {  # make em look nice
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Project name (e.g., "AI Models Research")'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What is this project about?'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',  # color picker
                'title': 'Choose project color theme'
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ScrapeEditForm(forms.ModelForm):
    """Form for editing scrape details and organization"""
    
    class Meta:
        model = UserScrape  # need to import this
        fields = ['project', 'notes', 'tags', 'is_bookmarked']
        widgets = {
            'project': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add notes about this scrape...'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'machine learning, datasets, nlp (comma separated)'
            }),
            'is_bookmarked': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:  # filter projects to current user only
            self.fields['project'].queryset = ScrapingProject.objects.filter(user=user)


class DataItemNotesForm(forms.ModelForm):
    """Form for adding notes to individual scraped items"""
    
    class Meta:
        model = ScrapedDataItem  # need to import this
        fields = ['user_notes', 'is_starred']
        widgets = {
            'user_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Add your notes about this dataset...'
            }),
            'is_starred': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
