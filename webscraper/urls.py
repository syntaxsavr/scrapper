from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views  # main views
from .profile_views_package import account_views, payment_views  # profile stuff

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

    # API URLs - background tasks
    path("api/search/", views.api_search, name="api_search"),  # start search
    path("api/status/<str:task_id>/", views.api_task_status, name="api_task_status"),  # check task status
    path("api/scrape-hugging-face-search/", views.api_scrape_hugging_face_search,  # scrape huggingface
         name="api_scrape_hugging_face_search")
]
