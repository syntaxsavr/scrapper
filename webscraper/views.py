from django.shortcuts import render, redirect
from .tasks import background_work
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from .models import Log

def home_view(request):
    search = request.GET.get("search", "")
    context = {
        "search": search,
    }
    return render(request, "home.html", context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = AuthenticationForm()
        
    context = {
        "form": form
    }
    return render(request, "login.html", context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()

    context = {
        "form": form
    }
    return render(request, "signup.html", context)

def index(request):
    if request.method == 'POST':
        background_work.delay()
    logs = Log.objects.all().order_by('-created_at')[:5]
    return render(request, 'webscraper/index.html', {
        'logs': logs, 
        'environment': ENVIRONMENT
    })