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
    # simple home view - profile context handled by context processor now
    return render(request, "home.html")

def api_search(request):
    query = request.GET.get("q", "")  # get search term

    if not query:  # need something to search
        return JsonResponse({"error": "No query provided"}, status=400)

    # create or get existing user scrape record if user is logged in
    user_scrape = None
    if request.user.is_authenticated:
        from .models import UserScrape  # import here to avoid circular imports
        from django.utils import timezone
        from datetime import timedelta
        
        # Check if user has a recent scrape with the same query (within last hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        existing_scrape = UserScrape.objects.filter(
            user=request.user,
            query__iexact=query,  # case-insensitive match
            started_at__gte=one_hour_ago
        ).first()
        
        if existing_scrape:
            # Reuse existing scrape
            user_scrape = existing_scrape
            user_scrape.status = 'pending'  # reset status
            user_scrape.started_at = timezone.now()  # update timestamp
            user_scrape.save()
        else:
            # Create new scrape
            user_scrape = UserScrape.objects.create(
                user=request.user,
                query=query,
                source='hugging_face',
                status='pending'
            )

    task = search_datasets.delay(query, user_scrape.id if user_scrape else None)  # pass scrape id to task

    response_data = {  # return task info
        "task_id": task.id,
        "status": "started",
        "message": f"Search started for '{query}'",
    }
    
    if user_scrape:  # include scrape info for logged in users
        response_data["scrape_id"] = user_scrape.id

    return JsonResponse(response_data)

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
        if task.successful():  # task completed successfully
            result = task.result

            results = Dataset.objects.filter(  # get matching datasets
                id__in=[r["id"] for r in result["results"]]
            )

            return JsonResponse({
                "status": "completed",
                "count": result["count"],
                "results": list(results.values("id", "title", "description")),
            })
        else:  # task failed
            error_info = str(task.info) if task.info else "Unknown error occurred"
            return JsonResponse({
                "status": "failed",
                "error": error_info,
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



