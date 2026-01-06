from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
    path("api/search/", views.api_search, name="api_search"),
    path("api/status/<str:task_id>/", views.api_task_status, name="api_task_status"),
]
