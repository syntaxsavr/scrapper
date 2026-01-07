from celery import shared_task
from .utils.hugging_face.fetch_datasets import fetch_huggingface_datasets
from .models import Dataset
from scrapers.kaggle.scraper_kaggle import KaggleScraperSelenium
from threading import Lock

lock = Lock()


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
        print("Added ")
        print(added_count)
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