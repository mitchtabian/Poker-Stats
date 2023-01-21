from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views

from account.views import (
    login_view,
    register_view,
)
from root.views import root_view

urlpatterns = [
    path('', root_view, name="home"),
    path('admin/', admin.site.urls),
    path('login/', login_view, name="login"),
    path("register", register_view, name="register"),
    path('verification/', include('verify_email.urls')),
]
