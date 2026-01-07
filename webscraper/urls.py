from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views  # main views
from .profile_views_package import account_views, payment_views  # profile stuff
from .profile_views_package import scraping_views  # scraping system

urlpatterns = [
    path("", views.home_view, name="home"),  # homepage
    path("detailed_view/<int:id>/", views.detailed_view, name="detailed_view"),  # dataset details
    path("login/", views.login_view, name="login"),  # login page
    path("signup/", views.signup_view, name="signup"),  # signup page
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),  # logout

    # Profile management URLs - new modular views
    path("profile/", account_views.profile_view, name="profile"),  # main profile
    path("profile/edit/", account_views.edit_profile_view, name="edit_profile"),  # edit profile
    path("profile/change-username/", account_views.change_username_view, name="change_username"),  # username change
    path("api/profile/", account_views.profile_api, name="profile_api"),  # profile data for dropdown
    
    # Payment method URLs - mock payment system
    path("payment-methods/", payment_views.payment_methods_view, name="payment_methods"),  # list cards
    path("payment-methods/add/", payment_views.add_payment_method_view, name="add_payment_method"),  # add card
    path("payment-methods/edit/<int:payment_id>/", payment_views.edit_payment_method_view, name="edit_payment_method"),  # edit card
    path("payment-methods/delete/<int:payment_id>/", payment_views.delete_payment_method_view, name="delete_payment_method"),  # delete card

    # Scraping Organization URLs - complete system for data management
    path("dashboard/", scraping_views.dashboard_view, name="dashboard"),  # main scraping dashboard
    path("projects/", scraping_views.projects_view, name="projects"),  # list all projects
    path("projects/create/", scraping_views.create_project_view, name="create_project"),  # create new project
    path("projects/<int:project_id>/", scraping_views.project_detail_view, name="project_detail"),  # project details
    path("projects/<int:project_id>/edit/", scraping_views.edit_project_view, name="edit_project"),  # edit project
    path("scrapes/", scraping_views.scrapes_view, name="scrapes"),  # list all scrapes
    path("scrapes/<int:scrape_id>/", scraping_views.scrape_detail_view, name="scrape_detail"),  # scrape details
    path("scrapes/<int:scrape_id>/edit/", scraping_views.edit_scrape_view, name="edit_scrape"),  # edit scrape
    path("scrapes/<int:scrape_id>/delete/", scraping_views.delete_scrape, name="delete_scrape"),  # delete scrape
    path("api/scraping-stats/", scraping_views.stats_api_view, name="scraping_stats_api"),  # stats for charts
    
    # Scraping API endpoints - interactive actions
    path("api/scrapes/<int:scrape_id>/bookmark/", scraping_views.toggle_bookmark_api, name="toggle_bookmark"),  # bookmark toggle
    path("api/items/<int:item_id>/star/", scraping_views.toggle_star_api, name="toggle_star"),  # star toggle
    path("api/scrapes/<int:scrape_id>/add-to-project/", scraping_views.add_scrape_to_project, name="add_scrape_to_project"),  # project management
    path("api/scrapes/<int:scrape_id>/cancel/", scraping_views.cancel_scrape, name="cancel_scrape"),  # cancel running scrape
    path("api/scrapes/<int:scrape_id>/rerun/", scraping_views.rerun_scrape, name="rerun_scrape"),  # rerun scrape
    path("api/scrapes/<int:scrape_id>/schedule/", scraping_views.update_scrape_schedule, name="update_scrape_schedule"),  # update schedule

    # API URLs - background tasks
    path("api/search/", views.api_search, name="api_search"),  # start search
    path("api/status/<str:task_id>/", views.api_task_status, name="api_task_status"),  # check task status
]
