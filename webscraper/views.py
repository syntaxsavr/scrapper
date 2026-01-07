from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .tasks import search_datasets, run_hugging_face_search_task, scrape_kaggle_task
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from .models import Dataset
from celery.result import AsyncResult

def home_view(request):
    return render(request, "home.html")

def api_search(request):
    query = request.GET.get("q", "")

    if not query:
        return JsonResponse({"error": "No query provided"}, status=400)

    task = search_datasets.delay(query)

    return JsonResponse({
        "task_id": task.id,
        "status": "started",
        "message": f"Search started for '{query}'",
    })

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

def detailed_view(request, id):
    dataset = get_object_or_404(Dataset, id=id)

    context = {
        "dataset": dataset
    }
    return render(request, "detailed_view.html", context)

def api_task_status(_, task_id):
    task = AsyncResult(task_id)

    if task.ready():
        result = task.result

        results = Dataset.objects.filter(
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

@require_GET
def api_scrape_kaggle_search(request):
    query = request.GET.get("q", "")
    if not query:
        return JsonResponse({"error": "Query parameter 'q' is required."}, status=400)
    
    if len(query) > 500:
        return JsonResponse({"error": "Query parameter 'q' is too long (max 500 characters)."}, status=400)
    
    limit_str = request.GET.get("limit", "200")

    try:
        limit = int(limit_str)
    except (Exception):
        return JsonResponse({"error": "Query parameter 'limit' must be a valid integer."}, status=400)

    task = scrape_kaggle_task.delay(query,limit)

    return JsonResponse({
        "message": f"Scraping Kaggle datasets for '{query,limit}' started",
        "task_id": task.id,
        "status": "started"
    })