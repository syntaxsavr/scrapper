import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_project.settings')
app = Celery('scraper_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_routes = {
    'scrapers.tasks.scrape_kaggle_task': {'queue': 'scraping'}
}
app.conf.task_default_queue = 'celery'

app.autodiscover_tasks()
