from django.shortcuts import render
from .tasks import background_work
from .models import Log

def home_view(request):
    search = request.GET.get("search", "")
    context = {
        "search": search,
    }
    return render(request, "home.html", context)

def index(request):
    if request.method == 'POST':
        background_work.delay()
    logs = Log.objects.all().order_by('-created_at')[:5]
    return render(request, 'webscraper/index.html', {
        'logs': logs, 
        'environment': ENVIRONMENT
    })
