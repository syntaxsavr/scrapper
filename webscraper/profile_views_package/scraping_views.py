from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from ..models import UserScrape, ScrapingProject, ScrapedDataItem  # scraping models
from ..forms import ScrapingProjectForm, ScrapeEditForm


@login_required
def dashboard_view(request):
    """Main dashboard with scraping stats and overview"""
    user = request.user
    
    # get basic stats
    total_scrapes = UserScrape.objects.filter(user=user).count()
    total_projects = ScrapingProject.objects.filter(user=user).count()
    total_results = ScrapedDataItem.objects.filter(scrape__user=user).count()
    bookmarked_scrapes = UserScrape.objects.filter(user=user, is_bookmarked=True).count()
    
    # recent activity - last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_scrapes = UserScrape.objects.filter(user=user, started_at__gte=thirty_days_ago).count()
    
    # status breakdown
    status_stats = UserScrape.objects.filter(user=user).values('status').annotate(count=Count('status'))
    
    # recent scrapes for activity feed
    recent_activity = UserScrape.objects.filter(user=user)[:10]  # last 10 scrapes
    
    # favorite projects
    favorite_projects = ScrapingProject.objects.filter(user=user, is_favorite=True)[:5]
    
    context = {
        'total_scrapes': total_scrapes,
        'total_projects': total_projects,
        'total_results': total_results,
        'bookmarked_scrapes': bookmarked_scrapes,
        'recent_scrapes': recent_scrapes,
        'status_stats': status_stats,
        'recent_activity': recent_activity,
        'favorite_projects': favorite_projects,
    }
    return render(request, 'scraping/dashboard.html', context)


@login_required  
def projects_view(request):
    """List all user's scraping projects"""
    projects = ScrapingProject.objects.filter(user=request.user)  # get user's projects only
    
    context = {'projects': projects}
    return render(request, 'scraping/projects.html', context)


@login_required
def create_project_view(request):
    """Create new scraping project"""
    if request.method == 'POST':  # form submitted
        form = ScrapingProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user  # assign to current user
            project.save()
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('projects')
    else:
        form = ScrapingProjectForm()  # empty form
    
    context = {'form': form}
    return render(request, 'scraping/create_project.html', context)


@login_required
def project_detail_view(request, project_id):
    """View individual project with its scrapes"""
    project = get_object_or_404(ScrapingProject, id=project_id, user=request.user)  # make sure user owns it
    
    # get all scrapes for this project
    all_scrapes = project.scrapes.all()
    
    # get recent 10 scrapes for display
    recent_scrapes = all_scrapes[:10]
    
    # project stats
    total_scrapes = all_scrapes.count()
    
    # Sum up the results_count from all completed scrapes
    total_results = all_scrapes.filter(status='completed').aggregate(total=Sum('results_count'))['total'] or 0
    
    # Average results per completed scrape
    avg_results = all_scrapes.filter(status='completed').aggregate(avg=Avg('results_count'))['avg'] or 0
    
    context = {
        'project': project,
        'scrapes': recent_scrapes,
        'total_scrapes': total_scrapes,
        'total_results': total_results,
        'avg_results': round(avg_results, 1),
    }
    return render(request, 'scraping/project_detail.html', context)


@login_required
def edit_project_view(request, project_id):
    """Edit existing project"""
    project = get_object_or_404(ScrapingProject, id=project_id, user=request.user)  # make sure user owns it
    
    if request.method == 'POST':  # form submitted
        # Check if this is a delete request
        if 'delete_project' in request.POST:
            project_name = project.name
            project.delete()  # This will cascade delete all related scrapes
            messages.success(request, f'Project "{project_name}" has been deleted.')
            return redirect('projects')
        
        # Otherwise, handle regular edit
        form = ScrapingProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()  # update project
            messages.success(request, f'Project "{project.name}" updated successfully!')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ScrapingProjectForm(instance=project)  # load existing data
    
    context = {'form': form, 'project': project}
    return render(request, 'scraping/edit_project.html', context)


@login_required
def scrapes_view(request):
    """List all user's scrapes with filtering"""
    from celery.result import AsyncResult
    from datetime import timedelta
    
    scrapes = UserScrape.objects.filter(user=request.user)  # get user scrapes
    
    # Auto-fix stuck scrapes - check if they're really running
    stuck_threshold = timezone.now() - timedelta(minutes=30)
    potentially_stuck = scrapes.filter(
        status__in=['running', 'pending'],
        started_at__lt=stuck_threshold
    )
    
    for scrape in potentially_stuck:
        # Check if the celery task is actually still running
        if scrape.celery_task_id:
            task = AsyncResult(scrape.celery_task_id)
            if task.ready():  # Task is done
                if task.successful():
                    scrape.status = 'completed'
                    scrape.completed_at = timezone.now()
                    if scrape.started_at:
                        scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                else:
                    scrape.status = 'failed'
                    scrape.error_message = 'Task failed or was lost'
                    scrape.completed_at = timezone.now()
                    if scrape.started_at:
                        scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                scrape.save()
        else:
            # No task ID, must be stuck
            scrape.status = 'failed'
            scrape.error_message = 'Task was lost (no task ID)'
            scrape.completed_at = timezone.now()
            if scrape.started_at:
                scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
            scrape.save()
    
    # filtering options
    status_filter = request.GET.get('status')  # filter by status
    project_filter = request.GET.get('project')  # filter by project
    bookmarked_filter = request.GET.get('bookmarked')  # only bookmarked
    
    if status_filter:  # apply status filter
        scrapes = scrapes.filter(status=status_filter)
    
    if project_filter:  # apply project filter
        scrapes = scrapes.filter(project_id=project_filter)
        
    if bookmarked_filter == 'true':  # only bookmarked
        scrapes = scrapes.filter(is_bookmarked=True)
    
    # get projects for filter dropdown
    projects = ScrapingProject.objects.filter(user=request.user)
    
    context = {
        'scrapes': scrapes,
        'projects': projects,
        'current_status': status_filter,
        'current_project': project_filter,
        'current_bookmarked': bookmarked_filter,
    }
    return render(request, 'scraping/scrapes.html', context)


@login_required
def scrape_detail_view(request, scrape_id):
    """View individual scrape with all results"""
    from celery.result import AsyncResult
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)  # make sure user owns it
    
    # Auto-fix if scrape is stuck
    if scrape.status in ['running', 'pending']:
        stuck_threshold = timezone.now() - timedelta(minutes=30)
        if scrape.started_at < stuck_threshold:
            # Check if the celery task is actually still running
            if scrape.celery_task_id:
                task = AsyncResult(scrape.celery_task_id)
                if task.ready():  # Task is done
                    if task.successful():
                        scrape.status = 'completed'
                        scrape.completed_at = timezone.now()
                        if scrape.started_at:
                            scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                    else:
                        scrape.status = 'failed'
                        scrape.error_message = 'Task failed or was lost'
                        scrape.completed_at = timezone.now()
                        if scrape.started_at:
                            scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                    scrape.save()
            else:
                # No task ID, must be stuck
                scrape.status = 'failed'
                scrape.error_message = 'Task was lost (no task ID)'
                scrape.completed_at = timezone.now()
                if scrape.started_at:
                    scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
                scrape.save()
    
    # get scraped items with search and filtering
    from django.core.paginator import Paginator
    
    items = scrape.items.all().order_by('-created_at')  # all items from this scrape, newest first
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    # Filter by starred
    show_starred_only = request.GET.get('starred', '').lower() == 'true'
    if show_starred_only:
        items = items.filter(is_starred=True)
    
    starred_items = scrape.items.filter(is_starred=True)  # user starred items
    
    # pagination - 20 items per page
    paginator = Paginator(items, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # get all user projects for the dropdown
    all_projects = ScrapingProject.objects.filter(user=request.user)
    
    context = {
        'scrape': scrape,
        'page_obj': page_obj,
        'items': page_obj,  # for template compatibility
        'starred_items': starred_items,
        'total_items': scrape.items.count(),  # total without filters
        'filtered_items': items.count(),  # total with filters
        'starred_count': starred_items.count(),
        'all_projects': all_projects,  # add projects for dropdown
        'search_query': search_query,
        'show_starred_only': show_starred_only,
    }
    return render(request, 'scraping/scrape_detail.html', context)


@login_required
def edit_scrape_view(request, scrape_id):
    """Edit scrape organization details"""
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)  # make sure user owns it
    
    if request.method == 'POST':  # form submitted
        form = ScrapeEditForm(request.POST, instance=scrape, user=request.user)
        if form.is_valid():
            form.save()  # save changes
            messages.success(request, 'Scrape updated successfully!')
            return redirect('scrape_detail', scrape_id=scrape.id)
    else:
        form = ScrapeEditForm(instance=scrape, user=request.user)  # load current data
    
    context = {'form': form, 'scrape': scrape}
    return render(request, 'scraping/edit_scrape.html', context)


@login_required
def stats_api_view(request):
    """API endpoint for dashboard statistics charts"""
    user = request.user
    
    # scrapes by month for last 6 months
    monthly_stats = []
    
    for i in range(6):  # last 6 months
        month_start = timezone.now() - timedelta(days=30*(i+1))
        month_end = timezone.now() - timedelta(days=30*i)
        
        count = UserScrape.objects.filter(
            user=user,
            started_at__gte=month_start,
            started_at__lt=month_end
        ).count()
        
        monthly_stats.append({
            'month': month_start.strftime('%b %Y'),
            'scrapes': count
        })
    
    monthly_stats.reverse()  # oldest first for chart
    
    # status distribution
    status_distribution = list(UserScrape.objects.filter(user=user).values('status').annotate(count=Count('status')))
    
    # most active projects
    project_stats = list(
        ScrapingProject.objects.filter(user=user)
        .annotate(scrape_count=Count('scrapes'))
        .values('name', 'scrape_count', 'color')
        .order_by('-scrape_count')[:5]  # top 5 projects
    )
    
    return JsonResponse({  # return json for charts
        'monthly_stats': monthly_stats,
        'status_distribution': status_distribution,
        'project_stats': project_stats,
    })


@login_required
def toggle_bookmark_api(request, scrape_id):
    """API endpoint to toggle bookmark status of a scrape"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    scrape.is_bookmarked = not scrape.is_bookmarked
    scrape.save()
    
    return JsonResponse({
        'success': True,
        'is_bookmarked': scrape.is_bookmarked,
        'message': 'Bookmarked' if scrape.is_bookmarked else 'Bookmark removed'
    })


@login_required
def toggle_star_api(request, item_id):
    """API endpoint to toggle star status of a scraped item"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    item = get_object_or_404(ScrapedDataItem, id=item_id, scrape__user=request.user)
    item.is_starred = not item.is_starred
    item.save()
    
    return JsonResponse({
        'success': True,
        'is_starred': item.is_starred,
        'message': 'Starred' if item.is_starred else 'Star removed'
    })


@login_required
def add_scrape_to_project(request, scrape_id):
    """Add an existing scrape to a project"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    project_id = request.POST.get('project_id')
    
    if project_id:
        project = get_object_or_404(ScrapingProject, id=project_id, user=request.user)
        scrape.project = project
        scrape.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Scrape added to project "{project.name}"',
            'project_name': project.name
        })
    else:
        # Remove from project
        scrape.project = None
        scrape.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Scrape removed from project'
        })


@login_required
def delete_scrape(request, scrape_id):
    """Delete a scrape and all its items"""
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    
    if request.method == 'POST':
        query = scrape.query
        scrape.delete()  # This will cascade delete all ScrapedDataItem objects
        messages.success(request, f'Scrape "{query}" has been deleted.')
        return redirect('scrapes')
    
    return redirect('edit_scrape', scrape_id=scrape_id)


@login_required
def cancel_scrape(request, scrape_id):
    """Cancel a running scrape"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    
    # Only cancel if it's running or pending
    if scrape.status not in ['running', 'pending']:
        return JsonResponse({
            'success': False,
            'message': f'Cannot cancel scrape with status: {scrape.status}'
        })
    
    # Cancel the celery task if we have a task ID
    if scrape.celery_task_id:
        from celery import current_app
        current_app.control.revoke(scrape.celery_task_id, terminate=True)
    
    # Update scrape status
    scrape.status = 'cancelled'
    scrape.completed_at = timezone.now()
    if scrape.started_at:
        scrape.duration_seconds = (timezone.now() - scrape.started_at).total_seconds()
    scrape.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Scrape cancelled successfully'
    })


@login_required
def rerun_scrape(request, scrape_id):
    """Rerun an existing scrape with the same query"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    
    # Create a new scrape with the same query and settings
    from ..tasks import search_datasets, scrap_huggingface_datasets
    
    new_scrape = UserScrape.objects.create(
        user=request.user,
        project=scrape.project,
        query=scrape.query,
        source=scrape.source,
        status='pending',
        schedule_frequency=scrape.schedule_frequency,
        is_scheduled_active=scrape.is_scheduled_active,
    )
    
    # Start the scraping tasks
    local_task = search_datasets.delay(scrape.query, new_scrape.id)
    hf_task = scrap_huggingface_datasets.delay(scrape.query, new_scrape.id)
    kg_task = scrap_huggingface_datasets.delay(scrape.query, new_scrape.id)
    
    # Store task ID
    new_scrape.celery_task_id = hf_task.id
    new_scrape.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Scrape started successfully',
        'scrape_id': new_scrape.id,
        'task_ids': [local_task.id, hf_task.id, kg_task.id]
    })


@login_required
def update_scrape_schedule(request, scrape_id):
    """Update the schedule settings for a scrape"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    
    frequency = request.POST.get('frequency', 'none')
    is_active = request.POST.get('is_active', 'false').lower() == 'true'
    
    # Validate frequency
    valid_frequencies = [choice[0] for choice in UserScrape.SCHEDULE_CHOICES]
    if frequency not in valid_frequencies:
        return JsonResponse({
            'success': False,
            'message': 'Invalid frequency'
        })
    
    scrape.schedule_frequency = frequency
    scrape.is_scheduled_active = is_active
    
    # Calculate next run time if activating
    if is_active and frequency != 'none':
        from datetime import timedelta
        
        now = timezone.now()
        if frequency == 'hourly':
            scrape.next_run_at = now + timedelta(hours=1)
        elif frequency == 'daily':
            scrape.next_run_at = now + timedelta(days=1)
        elif frequency == 'weekly':
            scrape.next_run_at = now + timedelta(weeks=1)
        elif frequency == 'monthly':
            scrape.next_run_at = now + timedelta(days=30)
        
        scrape.last_run_at = now
    else:
        scrape.next_run_at = None
    
    scrape.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Schedule updated successfully',
        'next_run': scrape.next_run_at.isoformat() if scrape.next_run_at else None
    })


@login_required
def export_scrape_csv(request, scrape_id):
    """Export scrape data as CSV"""
    import csv
    from django.http import HttpResponse
    
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)
    
    # Get all items (apply same filters as the view if provided)
    items = scrape.items.all().order_by('-created_at')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '').strip()
    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    # Apply starred filter if provided
    show_starred_only = request.GET.get('starred', '').lower() == 'true'
    if show_starred_only:
        items = items.filter(is_starred=True)
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    filename = f'scrape_{scrape.id}_{scrape.query}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'ID',
        'Title',
        'Description',
        'URL',
        'Author',
        'Tags',
        'Downloads',
        'Likes',
        'Is Starred',
        'User Notes',
        'Created At',
    ])
    
    # Write data rows
    for item in items:
        writer.writerow([
            item.id,
            item.title,
            item.description,
            item.url,
            item.author or '',
            item.tags or '',
            item.downloads if item.downloads is not None else '',
            item.likes if item.likes is not None else '',
            'Yes' if item.is_starred else 'No',
            item.user_notes or '',
            item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
        ])
    
    return response
