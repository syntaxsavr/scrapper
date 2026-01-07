from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .tasks import search_datasets, scrap_huggingface_datasets
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from .models import Dataset
from .forms import CustomUserCreationForm  # signup form
from celery.result import AsyncResult

def home_view(request):
    # simple home view - profile context handled by context processor now
    return render(request, "home.html")

def api_search(request):
    query = request.GET.get("q", "")  # get search term

    if not query:  # need something to search
        return JsonResponse({"error": "No query provided"}, status=400)

    # Create user scrape record if user is authenticated
    user_scrape_id = None
    if request.user.is_authenticated:
        from .models import UserScrape
        from django.utils import timezone
        
        user_scrape = UserScrape.objects.create(
            user=request.user,
            query=query,
            source='hugging_face',
            status='pending'
        )
        user_scrape_id = user_scrape.id

    # Start both search tasks in parallel (pass user_scrape_id if exists)
    local_task = search_datasets.delay(query, user_scrape_id)
    hf_task = scrap_huggingface_datasets.delay(query, user_scrape_id)

    response_data = {
        "task_ids": [local_task.id, hf_task.id],
        "status": "started",
        "message": f"Search started for '{query}'",
    }
    
    if user_scrape_id:
        response_data["scrape_id"] = user_scrape_id

    return JsonResponse(response_data)

def api_task_status(_, task_id):
    task = AsyncResult(task_id)

    if task.ready():
        if task.successful():
            result = task.result
            response = {"status": "completed"}

            # Pass through all fields from the task result
            if isinstance(result, dict):
                if "results" in result:
                    response["results"] = result["results"]
                if "retrigger_task_id" in result:
                    response["retrigger_task_id"] = result["retrigger_task_id"]
                if "count" in result:
                    response["count"] = result["count"]
                if "query" in result:
                    response["query"] = result["query"]

            return JsonResponse(response)
        else:
            # Task failed
            error_info = str(task.info) if task.info else "Unknown error occurred"
            return JsonResponse({
                "status": "failed",
                "error": error_info,
            })
    else:
        return JsonResponse({
            "status": "pending",
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



