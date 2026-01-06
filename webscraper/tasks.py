from celery import shared_task
from .utils.hugging_face.fetch_datasets import fetch_huggingface_datasets
from .models import Dataset

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

@shared_task
def run_hugging_face_search_task(query: str, limit: int = 50):
    scraped_items = fetch_huggingface_datasets(query=query, limit=limit)
    added_count = 0

    for item in scraped_items:
        if not Dataset.objects.filter(title=item["title"]).exists():
            Dataset.objects.create(title=item["title"], description=item["description"])
            added_count += 1

    return {
        "query": query,
        "total_scraped": len(scraped_items),
        "added": added_count
    }
