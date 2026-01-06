from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from ..models import UserScrape, ScrapingProject, ScrapedDataItem  # scraping models
from ..forms import ScrapingProjectForm, ScrapeEditForm, DataItemNotesForm


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
    
    # get project scrapes with pagination maybe
    scrapes = project.scrapes.all()  # get all scrapes in this project
    
    # project stats
    total_scrapes = scrapes.count()
    total_results = ScrapedDataItem.objects.filter(scrape__in=scrapes).count()
    avg_results = scrapes.filter(status='completed').aggregate(avg=Avg('results_count'))['avg'] or 0
    
    context = {
        'project': project,
        'scrapes': scrapes,
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
    scrapes = UserScrape.objects.filter(user=request.user)  # get user scrapes
    
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
    scrape = get_object_or_404(UserScrape, id=scrape_id, user=request.user)  # make sure user owns it
    
    # get scraped items
    items = scrape.items.all()  # all items from this scrape
    starred_items = items.filter(is_starred=True)  # user starred items
    
    context = {
        'scrape': scrape,
        'items': items,
        'starred_items': starred_items,
        'total_items': items.count(),
        'starred_count': starred_items.count(),
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
    six_months_ago = timezone.now() - timedelta(days=180)
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
