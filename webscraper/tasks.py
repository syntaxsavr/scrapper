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
def search_datasets(query, user_scrape_id=None, is_retrigger=False):
    """Search existing datasets with scoring"""
    from django.utils import timezone
    start_time = timezone.now()
    
    # Update user scrape status if provided (but not for retriggers)
    if user_scrape_id and not is_retrigger:
        try:
            from .models import UserScrape
            scrape = UserScrape.objects.get(id=user_scrape_id)
            scrape.status = 'running'
            scrape.save()
        except Exception:
            pass  # Continue even if scrape update fails
    
    try:
        results_with_scores = _perform_search_with_scoring(query)
        
        # Update user scrape with results if provided
        if user_scrape_id:
            try:
                from .models import UserScrape, ScrapedDataItem
                scrape = UserScrape.objects.get(id=user_scrape_id)
                
                # Only update status to completed if this is not a retrigger
                # Retriggers just update the results without changing status
                if not is_retrigger:
                    scrape.status = 'completed'
                    scrape.completed_at = timezone.now()
                    scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
                
                scrape.results_count = len(results_with_scores)
                scrape.results_data = {'results': results_with_scores}
                scrape.save()
                
                # Create ScrapedDataItem records (only if not already created)
                if not is_retrigger:
                    for result in results_with_scores[:50]:  # Limit to first 50
                        ScrapedDataItem.objects.create(
                            scrape=scrape,
                            title=result['title'],
                            description=result['description'],
                            url=f"/detailed_view/{result['id']}/",
                        )
            except Exception:
                pass  # Continue even if scrape update fails

        return {
            "query": query,
            "results": results_with_scores
        }
    except Exception as e:
        # Update scrape to failed status
        if user_scrape_id:
            try:
                from .models import UserScrape
                scrape = UserScrape.objects.get(id=user_scrape_id)
                scrape.status = 'failed'
                scrape.error_message = str(e)
                scrape.completed_at = timezone.now()
                scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
                scrape.save()
            except Exception:
                pass
        raise

@shared_task(queue='celery')
def scrap_huggingface_datasets(query, user_scrape_id=None):
    """Scrape hugging face datasets and trigger a retrigger search"""
    from django.utils import timezone
    start_time = timezone.now()
    
    # Update user scrape status if provided
    if user_scrape_id:
        try:
            from .models import UserScrape
            scrape = UserScrape.objects.get(id=user_scrape_id)
            scrape.status = 'running'
            scrape.save()
        except Exception:
            pass
    
    try:
        scraped_items = fetch_huggingface_datasets(query=query, limit=50)
        added_count = 0

        for item in scraped_items:
            if not Dataset.objects.filter(title=item["title"]).exists():
                Dataset.objects.create(title=item["title"], description=item["description"])
                added_count += 1
        
        # Update user scrape with scraping results
        if user_scrape_id:
            try:
                from .models import UserScrape, ScrapedDataItem
                scrape = UserScrape.objects.get(id=user_scrape_id)
                scrape.results_count = len(scraped_items)
                scrape.results_data = {
                    'scraped_items': scraped_items[:50],  # Limit stored data
                    'added_count': added_count
                }
                scrape.save()
                
                # Create ScrapedDataItem records for scraped items
                for item in scraped_items[:50]:  # Limit to first 50
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
            except Exception:
                pass

        # Trigger a new search with the updated data (mark as retrigger)
        retrigger_task = search_datasets.delay(query, user_scrape_id, is_retrigger=True)
        
        # Wait for retrigger to complete and then mark main scrape as completed
        if user_scrape_id:
            try:
                from .models import UserScrape
                scrape = UserScrape.objects.get(id=user_scrape_id)
                scrape.status = 'completed'
                scrape.completed_at = timezone.now()
                scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
                scrape.save()
            except Exception:
                pass

        return {
            "retrigger_task_id": retrigger_task.id
        }
    except Exception as e:
        # Update scrape to failed status
        if user_scrape_id:
            try:
                from .models import UserScrape
                scrape = UserScrape.objects.get(id=user_scrape_id)
                scrape.status = 'failed'
                scrape.error_message = str(e)
                scrape.completed_at = timezone.now()
                scrape.duration_seconds = (timezone.now() - start_time).total_seconds()
                scrape.save()
            except Exception:
                pass
        raise
