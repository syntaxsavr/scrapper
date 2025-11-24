from celery import shared_task

from scrapers.kaggle.kaggle_scraper import KaggleScraper
from scrapper_project.settings import ENVIRONMENT
from .models import Log
import time

@shared_task
def background_work():
    time.sleep(2)
    Log.objects.create(message=f"Task completed in {ENVIRONMENT}!")
    return "Done"


@shared_task
def run_kaggle_scraper():
    scraper = KaggleScraper()
    try:
        datasets = scraper.scrape()
        Log.objects.create(message=f"Kaggle scraped {len(datasets)} datasets")
    except Exception as e:
        Log.objects.create(message=f"Kaggle scraper error: {str(e)}")
