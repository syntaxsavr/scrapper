from celery import shared_task
from .models import Log
import time

@shared_task
def background_work():
    time.sleep(2)
    Log.objects.create(message=f"Task completed in {ENVIRONMENT}!")
    return "Done"
