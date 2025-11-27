from celery import shared_task
from .models import Log, Dataset
import time

@shared_task
def search_datasets(query):
    from django.db.models import Q
    results = Dataset.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )

    count = results.count()

    return {
        "query": query,
        "count": count,
        "results": list(results.values("id", "title", "description"))
    }
