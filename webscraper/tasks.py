from celery import shared_task
from .utils.hugging_face.fetch_datasets import fetch_huggingface_datasets
from .models import Dataset
from django.utils import timezone

@shared_task
def search_datasets(query, user_scrape_id=None):
    """Search existing datasets and optionally update user scrape record"""
    from django.db.models import Q
    
    start_time = timezone.now()  # track timing
    
    # update scrape status to running if we have a scrape record
    if user_scrape_id:
        try:
            from .models import UserScrape
            scrape = UserScrape.objects.get(id=user_scrape_id)
            scrape.status = 'running'  # mark as running
            scrape.save()
        except UserScrape.DoesNotExist:
            pass  # scrape record not found, continue anyway
    
    # perform the search
    results = Dataset.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )

    count = results.count()
    results_data = list(results.values("id", "title", "description"))
    
    # update scrape record with results if we have one
    if user_scrape_id:
        try:
            scrape = UserScrape.objects.get(id=user_scrape_id)
            scrape.status = 'completed'  # mark as completed
            scrape.results_count = count
            scrape.results_data = {'results': results_data}  # store results
            scrape.completed_at = timezone.now()
            scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
            scrape.save()
            
            # create ScrapedDataItem records for each result
            from .models import ScrapedDataItem
            for result in results_data:
                ScrapedDataItem.objects.create(
                    scrape=scrape,
                    title=result['title'],
                    description=result['description'],
                    url=f"/detailed_view/{result['id']}/",  # link to detail view
                )
                
        except UserScrape.DoesNotExist:
            pass

    return {
        "query": query,
        "count": count,
        "results": results_data
    }

@shared_task
def run_hugging_face_search_task(query: str, limit: int = 50, user_scrape_id=None):
    """Scrape hugging face datasets and optionally update user scrape record"""
    start_time = timezone.now()  # track timing
    
    # update scrape status if we have a scrape record
    if user_scrape_id:
        try:
            from .models import UserScrape
            scrape = UserScrape.objects.get(id=user_scrape_id)
            scrape.status = 'running'  # mark as running
            scrape.save()
        except UserScrape.DoesNotExist:
            pass
    
    try:
        scraped_items = fetch_huggingface_datasets(query=query, limit=limit)
        added_count = 0

        for item in scraped_items:
            if not Dataset.objects.filter(title=item["title"]).exists():
                Dataset.objects.create(title=item["title"], description=item["description"])
                added_count += 1

        # update scrape record with success
        if user_scrape_id:
            try:
                scrape = UserScrape.objects.get(id=user_scrape_id)
                scrape.status = 'completed'
                scrape.results_count = len(scraped_items)
                scrape.results_data = {'scraped_items': scraped_items, 'added_count': added_count}
                scrape.completed_at = timezone.now()
                scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
                scrape.save()
                
                # create ScrapedDataItem records
                from .models import ScrapedDataItem
                for item in scraped_items:
                    ScrapedDataItem.objects.create(
                        scrape=scrape,
                        title=item['title'],
                        description=item.get('description', ''),
                        url=item.get('url', ''),
                        downloads=item.get('downloads'),
                        likes=item.get('likes'),
                        author=item.get('author', ''),
                        tags=item.get('tags', ''),
                    )
            except UserScrape.DoesNotExist:
                pass

        return {
            "query": query,
            "scraped_count": len(scraped_items),
            "added_count": added_count,
            "items": scraped_items
        }
        
    except Exception as e:
        # handle errors and update scrape record
        if user_scrape_id:
            try:
                scrape = UserScrape.objects.get(id=user_scrape_id)
                scrape.status = 'failed'
                scrape.error_message = str(e)
                scrape.completed_at = timezone.now()
                scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
                scrape.save()
            except UserScrape.DoesNotExist:
                pass
        
        raise e  # re-raise the error
