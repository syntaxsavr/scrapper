from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .tasks import search_datasets, scrap_huggingface_datasets, scrape_kaggle_task
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from .models import Dataset
from .forms import CustomUserCreationForm  # signup form
from celery.result import AsyncResult
from datetime import timedelta

def home_view(request):
    # simple home view - profile context handled by context processor now
    return render(request, "home.html")

def api_search(request):
    query = request.GET.get("q", "")  # get search term

    if not query:  # need something to search
        return JsonResponse({"error": "No query provided"}, status=400)

    # Check for existing scrapes ONLY if user is authenticated
    if request.user.is_authenticated:
        from .models import UserScrape
        from django.utils import timezone
        
        # Check if user already has a scrape with the exact same query
        existing_scrape = UserScrape.objects.filter(
            user=request.user,
            query=query
        ).order_by('-started_at').first()
        
        if existing_scrape:
            # If there's a recent scrape (less than 1 hour old), suggest rerunning
            one_hour_ago = timezone.now() - timedelta(hours=1)
            if existing_scrape.started_at > one_hour_ago:
                return JsonResponse({
                    "status": "duplicate",
                    "message": f"You already have a scrape for '{query}' from {existing_scrape.started_at.strftime('%H:%M')}.",
                    "scrape_id": existing_scrape.id,
                    "existing": True
                })

    # Start only the local search task initially (fast results)
    # Don't create UserScrape automatically - user will choose to save later
    local_task = search_datasets.delay(query, user_scrape_id=None)
    
    # Also start HuggingFace scraping in the background to get more results
    # This populates the local database with new datasets
    huggingface_task = scrap_huggingface_datasets.delay(query, user_scrape_id=None)
    kaggle_task = scrape_kaggle_task.delay(query, 100, user_scrape_id=None)

    response_data = {
        "task_ids": [local_task.id, huggingface_task.id, kaggle_task.id],
        "status": "started",
        "message": f"Search started for '{query}'",
        "is_authenticated": request.user.is_authenticated
    }

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

def api_create_scrape(request):
    """Create a UserScrape from search results"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({"error": "POST method required"}, status=405)
    
    import json
    data = json.loads(request.body)
    query = data.get('query', '').strip()
    
    if not query:
        return JsonResponse({"error": "Query is required"}, status=400)
    
    from .models import UserScrape
    from django.utils import timezone
    
    # Check if user already has this exact scrape
    existing_scrape = UserScrape.objects.filter(
        user=request.user,
        query=query
    ).order_by('-started_at').first()
    
    if existing_scrape:
        # Check if it's recent (less than 5 minutes old)
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        if existing_scrape.started_at > five_minutes_ago:
            return JsonResponse({
                "status": "duplicate",
                "message": "You already have a recent scrape for this query",
                "scrape_id": existing_scrape.id
            })
    
    # Create new user scrape
    user_scrape = UserScrape.objects.create(
        user=request.user,
        query=query,
        source='hugging_face',
        status='pending'
    )
    
    # Start the scraping task (HuggingFace scraping)
    hf_task = scrap_huggingface_datasets.delay(query, user_scrape.id)

    kg_task = scrape_kaggle_task.delay(query, 100, user_scrape.id)

    return JsonResponse({
        "task_ids": [hf_task.id, kg_task.id]
    })
    
    # Store task ID for tracking/cancellation
    user_scrape.celery_task_id = hf_task.id
    user_scrape.save()
    
    return JsonResponse({
        "status": "success",
        "message": "Scrape created successfully",
        "scrape_id": user_scrape.id,
        "task_id": hf_task.id
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



