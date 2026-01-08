from celery import shared_task
from django.db.models import Q
from .utils.hugging_face.fetch_datasets import fetch_huggingface_datasets
from .utils.search.scoring import calculate_search_score
from .models import Dataset
from scrapers.kaggle.scraper_kaggle import KaggleScraperSelenium
from threading import Lock

lock = Lock()


def _perform_search_with_scoring(query, limit=100):
    """Internal helper to perform search with scoring"""
    results = Dataset.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )
    
    # Get total count before limiting
    total_count = results.count()
    
    # Limit query to only fetch what we need
    results = results[:limit]

    results_with_scores = []
    for dataset in results:
        score = calculate_search_score(query, dataset.title, dataset.description)
        results_with_scores.append({
            "id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "source": dataset.source,
            "author": dataset.author,
            "downloads": dataset.downloads,
            "likes": dataset.likes,
            "tags": dataset.tags,
            "thumbnail": dataset.thumbnail,
            "url": dataset.url,
            "score": score
        })

    # Sort by score descending
    results_with_scores.sort(key=lambda x: x["score"], reverse=True)

    # Remove score from final results
    for result in results_with_scores:
        del result["score"]

    return results_with_scores, total_count

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
        results_with_scores, total_count = _perform_search_with_scoring(query, limit=100)
        
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
                
                # Store metadata about total results found
                scrape.results_data = {
                    'results': results_with_scores,
                    'total_count': total_count,
                    'displayed_count': len(results_with_scores)
                }
                scrape.save()
                
                # For retriggers, only delete items without author (local search results)
                # For initial runs, delete all items to start fresh
                if is_retrigger:
                    # Delete only local search items (no author field or empty author)
                    ScrapedDataItem.objects.filter(
                        scrape=scrape
                    ).filter(
                        Q(author__isnull=True) | Q(author='')
                    ).delete()
                else:
                    # Delete all existing items for this scrape to prevent duplicates on rerun
                    ScrapedDataItem.objects.filter(scrape=scrape).delete()
                
                # Create fresh ScrapedDataItem records with proper URLs
                # Use get_or_create to prevent duplicates on retrigger when item already exists from HuggingFace
                created_count = 0
                for result in results_with_scores:
                    # Check if this item already exists (from HuggingFace scraping)
                    existing = ScrapedDataItem.objects.filter(
                        scrape=scrape,
                        title=result['title']
                    ).first()
                    
                    if not existing:
                        # Only create if it doesn't exist
                        ScrapedDataItem.objects.create(
                            scrape=scrape,
                            title=result['title'],
                            description=result['description'],
                            url=f"/detailed_view/{result['id']}/",
                            source=result.get('source', 'unknown'),
                            author=result.get('author', ''),
                            tags=result.get('tags', ''),
                            downloads=result.get('downloads'),
                            likes=result.get('likes'),
                        )
                        created_count += 1
                
                # Update results_count to actual number of items in the scrape
                scrape.results_count = scrape.items.count()
                scrape.save()
            except Exception as e:
                print(f"Error updating scrape data: {e}")  # Log error
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
        # Fetch up to 100 datasets from HuggingFace
        scraped_items = fetch_huggingface_datasets(query=query, limit=100)
        added_count = 0

        for item in scraped_items:
            if not Dataset.objects.filter(title=item["title"]).exists():
                Dataset.objects.create(
                    title=item["title"],
                    description=item.get("description", ""),
                    source='huggingface',
                    author=item.get("author", ""),
                    tags=item.get("tags", ""),
                    downloads=item.get("downloads"),
                    likes=item.get("likes"),
                    url=item.get("url", ""),
                    thumbnail = ""
                )
                added_count += 1
            else:
                # Update existing dataset with latest info from HuggingFace
                dataset = Dataset.objects.get(title=item["title"])
                dataset.description = item.get("description", "")
                dataset.source = 'huggingface'
                dataset.author = item.get("author", "")
                dataset.tags = item.get("tags", "")
                dataset.downloads = item.get("downloads")
                dataset.likes = item.get("likes")
                dataset.url = item.get("url", "")
                dataset.save()
        
        # Update user scrape with scraping results
        if user_scrape_id:
            user_update_with_results(user_scrape_id, scraped_items, added_count, source='huggingface')

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


def user_update_with_results(user_scrape_id, scraped_items, added_count, source='unknown'):
    try:
        from .models import UserScrape, ScrapedDataItem
        scrape = UserScrape.objects.get(id=user_scrape_id)
        
        # Store metadata but don't set results_count yet
        scrape.results_data = {
            'scraped_items': scraped_items[:100],
            'added_count': added_count,
            'total_found': len(scraped_items)
        }
        scrape.save()
        
        # Delete existing items from this source for this scrape to prevent duplicates
        ScrapedDataItem.objects.filter(scrape=scrape, source=source).delete()
        
        # Create ScrapedDataItem records for scraped items (limit to 100)
        created_count = 0
        for item in scraped_items[:100]:
            # Check if this item already exists to prevent duplicates
            if ScrapedDataItem.objects.filter(scrape=scrape, title=item['title']).exists():
                continue
            
            # Find the Dataset in our DB to get the proper internal URL
            dataset = Dataset.objects.filter(title=item['title']).first()
            internal_url = f"/detailed_view/{dataset.id}/" if dataset else item.get('url', '')
            
            ScrapedDataItem.objects.create(
                scrape=scrape,
                title=item['title'],
                description=item.get('description', ''),
                url=internal_url,  # Use internal URL if available
                source=source,
                downloads=item.get('downloads'),
                likes=item.get('likes'),
                author=item.get('author', ''),
                tags=item.get('tags', ''),
            )
            created_count += 1
        
        # Update results_count to actual number of items in the scrape
        scrape.results_count = scrape.items.count()
        scrape.save()
        
    except Exception as e:
        print(f"Error updating scrape data: {e}")  # Log error
        pass


@shared_task(bind=True, max_retries=3, queue='scraping')
def scrape_kaggle_task(self, query: str, limit: int, user_scrape_id=None):

    # check if worker is running
    acquired = lock.acquire(blocking=False)
    if not acquired:
        raise self.retry(countdown=6)   # scrapes can take up to 5,5s
    
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
        scraper = KaggleScraperSelenium()
        results = scraper.scrape(query, limit)
        added_count = 0
        for item in results:
            if not Dataset.objects.filter(title=item["title"]).exists():
                Dataset.objects.create(
                    title=item["title"],
                    description=f"Uploaded to Kaggle on: {item['date']}",
                    source='kaggle',
                    url=item["link"],
                    thumbnail=item["thumbnail"],
                    author=item.get("author", ""),
                    tags=""
                )
                added_count += 1
            else:
                # Update existing dataset with latest info from Kaggle
                dataset = Dataset.objects.get(title=item["title"])
                dataset.description = f"Uploaded to Kaggle on: {item['date']}"
                dataset.source = 'kaggle'
                dataset.url = item["link"]
                dataset.thumbnail = item["thumbnail"]
                dataset.author = item.get("author", "")
                dataset.tags = ""
                dataset.save()
        
        # Update user scrape with scraping results
        if user_scrape_id:
            user_update_with_results(user_scrape_id, results, added_count, source='kaggle')

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
            "query": query,
            "total_scraped": len(results),
            "added": added_count,
            "retrigger_task_id": retrigger_task.id
        }
    
    except Exception as e:
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
    finally:
        if acquired:
            scraper.close()
            lock.release()
