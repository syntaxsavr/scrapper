from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .tasks import search_datasets, run_hugging_face_search_task  # celery tasks
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib import messages
from .models import Dataset, UserProfile  # our models
from .forms import CustomUserCreationForm  # signup form
from celery.result import AsyncResult

def home_view(request):
    context = {}
    if request.user.is_authenticated:  # if logged in
        profile, created = UserProfile.objects.get_or_create(  # get or make profile for dropdown
            user=request.user,
            defaults={'full_name': request.user.get_full_name() or request.user.username}
        )
        context['profile'] = profile  # pass to template
    return render(request, "home.html", context)

def api_search(request):
    query = request.GET.get("q", "")  # get search term

    if not query:  # need something to search
        return JsonResponse({"error": "No query provided"}, status=400)

    task = search_datasets.delay(query)  # start background task

    return JsonResponse({  # return task info
        "task_id": task.id,
        "status": "started",
        "message": f"Search started for '{query}'",
    })

def login_view(request):
    if request.user.is_authenticated:  # already logged in
        return redirect("home")
    
    if request.method == "POST":  # form submitted
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()  # get authenticated user
            login(request, user)  # log them in
            return redirect("home")  # go to homepage
    else:
        form = AuthenticationForm()  # empty login form
        
    context = {
        "form": form
    }
    return render(request, "accounts/login.html", context)

def signup_view(request):
    if request.user.is_authenticated:  # already logged in
        return redirect("home")

    if request.method == "POST":  # form submitted
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # create new user and profile
            login(request, user)  # auto login after signup
            messages.success(request, 'Account created successfully!')
            return redirect("home")
    else:
        form = CustomUserCreationForm()  # empty signup form

    context = {
        "form": form
    }
    return render(request, "accounts/signup.html", context)

def detailed_view(request, id):
    dataset = get_object_or_404(Dataset, id=id)  # get specific dataset

    context = {
        "dataset": dataset
    }
    return render(request, "detailed_view.html", context)

def api_task_status(_, task_id):
    task = AsyncResult(task_id)  # get celery task result

    if task.ready():  # task finished
        result = task.result

        results = Dataset.objects.filter(  # get matching datasets
            id__in=[r["id"] for r in result["results"]]
        )

        return JsonResponse({
            "status": "completed",
            "count": result["count"],
            "results": list(results.values("id", "title", "description")),
        })
    else:
        return JsonResponse({
            "status": "pending",
        })

@require_GET
def api_scrape_hugging_face_search(request):
    query = request.GET.get("q")
    if not query:
        return JsonResponse({"error": "Query parameter 'q' is required."}, status=400)

    limit = int(request.GET.get("limit", 50))

    task = run_hugging_face_search_task.delay(query, limit)

    return JsonResponse({
        "message": f"Scraping Hugging Face datasets for '{query}' started",
        "task_id": task.id,
        "status": "started",
        "limit": limit
    })



