from django.urls import path
from .views import register, EmailLoginView
from .password_views import PrettyPasswordResetView
from .profile_views import profile_page, telegram_connect_api


urlpatterns = [
    path("password_reset/", PrettyPasswordResetView.as_view(), name="password_reset"),
    path("register/", register, name="register"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("me/profile/", profile_page, name="profile_page"),
    path("telegram/connect/", telegram_connect_api, name="telegram_connect_api"),
]

