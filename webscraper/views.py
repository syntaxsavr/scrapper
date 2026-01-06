from django.shortcuts import render, redirect
from django.http import JsonResponse
from .tasks import search_datasets, scrap_huggingface_datasets
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from celery.result import AsyncResult

def home_view(request):
    return render(request, "home.html")

def api_search(request):
    query = request.GET.get("q", "")

    if not query:
        return JsonResponse({"error": "No query provided"}, status=400)

    local_task = search_datasets.delay(query)
    hf_task = scrap_huggingface_datasets.delay(query)

    return JsonResponse({
        "task_ids": [local_task.id, hf_task.id]
    })

def api_task_status(_request, task_id):
    task = AsyncResult(task_id)
    _ = _request

    if task.ready():
        result = task.result
        response = {"status": "completed"}

        if "results" in result:
            response["count"] = result["count"]
            response["results"] = result["results"]

        if "retrigger_task_id" in result:
            response["retrigger_task_id"] = result["retrigger_task_id"]

        return JsonResponse(response)
    else:
        return JsonResponse({
            "status": "pending",
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