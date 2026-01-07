from celery import shared_task
from django.db.models import Q
from .utils.hugging_face.fetch_datasets import fetch_huggingface_datasets
from .utils.search.scoring import calculate_search_score
from .models import Dataset
from scrapers.kaggle.scraper_kaggle import KaggleScraperSelenium
from threading import Lock

lock = Lock()


def _perform_search_with_scoring(query):
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

    results_with_scores.sort(key=lambda x: x["score"], reverse=True)

    for result in results_with_scores:
        del result["score"]

    return results_with_scores

@shared_task(queue='search')
def search_datasets(query):
    results_with_scores = _perform_search_with_scoring(query)

    return {
        "results": results_with_scores
    }

@shared_task(queue='celery')
def scrap_huggingface_datasets(query):
    scraped_items = fetch_huggingface_datasets(query=query, limit=50)

    for item in scraped_items:
        if not Dataset.objects.filter(title=item["title"]).exists():
            Dataset.objects.create(title=item["title"], description=item["description"])

    retrigger_task = search_datasets.delay(query)

    return {
        "retrigger_task_id": retrigger_task.id
    }

@shared_task(bind=True, max_retries=3, queue='scraping')
def scrape_kaggle_task(self, query: str, limit: int):
    acquired = lock.acquire(blocking=False)
    if not acquired:
        raise self.retry(countdown=6)   # scrapes can take up to 5,5s
    try:
        scraper = KaggleScraperSelenium()
        results = scraper.scrape(query, limit)
        added_count = 0
        for item in results:
            if not Dataset.objects.filter(title=item["title"]).exists():
                Dataset.objects.create(title=item["title"], description=item["link"])
                added_count += 1
        return {
            "query": query,
            "total_scraped": len(results),
            "added": added_count
        }
    except Exception:
        return {
            "query": query,
            "total_scraped": 0,
            "added": 0
        }
    finally:
        if acquired:
            scraper.close()
            lock.release()