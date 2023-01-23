from django.urls import include, path

from user.views import (
    cannot_edit_others_profile,
    user_profile_view,
)

app_name = 'user'

urlpatterns = [
    path('profile/<int:pk>', user_profile_view, name="profile"),
    path('cannot_edit_others_profile', cannot_edit_others_profile, name="cannot_edit_others_profile"),
]