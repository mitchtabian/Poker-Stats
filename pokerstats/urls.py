from django.contrib import admin
from django.urls import include, path

from root.views import root_view

urlpatterns = [
    path('', root_view, name="home"),
    path('accounts/', include("allauth.urls")),
    path('admin/', admin.site.urls),
]
