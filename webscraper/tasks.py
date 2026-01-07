from celery import shared_task
from django.db.models import Q
from .utils.hugging_face.fetch_datasets import fetch_huggingface_datasets
from .utils.search.scoring import calculate_search_score
from .models import Dataset

def _perform_search_with_scoring(query):
    """Internal helper to perform search with scoring"""
    results = Dataset.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )

    results_with_scores = []
    for dataset in results:
        score = calculate_search_score(query, dataset.title, dataset.description)
        results_with_scores.append({
            "id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "score": score
        })

    # Sort by score descending
    results_with_scores.sort(key=lambda x: x["score"], reverse=True)

    # Remove score from final results
    for result in results_with_scores:
        del result["score"]

    return results_with_scores

@shared_task(queue='search')
def search_datasets(query):
    """Search existing datasets with scoring"""
    results_with_scores = _perform_search_with_scoring(query)

    return {
        "query": query,
        "results": results_with_scores
    }

@shared_task(queue='celery')
def scrap_huggingface_datasets(query):
    """Scrape hugging face datasets and trigger a retrigger search"""
    scraped_items = fetch_huggingface_datasets(query=query, limit=50)
    added_count = 0

    for item in scraped_items:
        if not Dataset.objects.filter(title=item["title"]).exists():
            Dataset.objects.create(title=item["title"], description=item["description"])
            added_count += 1

    # Trigger a new search with the updated data
    retrigger_task = search_datasets.delay(query)

    return {
        "retrigger_task_id": retrigger_task.id
    }
