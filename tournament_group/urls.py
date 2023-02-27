from django.urls import include, path

from tournament_group.views import (
	add_tournament_to_group,
	add_user_to_group,
	remove_tournament_from_group,
	remove_user_from_group,
	tournament_group_create_view,
	tournament_group_update_view,
	update_tournament_group_title,
	view_tournament_group
)

app_name = 'tournament_group'

urlpatterns = [
    path('add_user_to_group/<int:user_id>/<int:tournament_group_id>/', add_user_to_group, name="add_user_to_group"),
    path('add_tourament_to_group/<int:tournament_id>/<int:tournament_group_id>/', add_tournament_to_group, name="add_tournament_to_group"),
    path('remove_tournament_from_group/<int:tournament_id>/<int:tournament_group_id>/', remove_tournament_from_group, name="remove_tournament_from_group"),
    path('create/', tournament_group_create_view, name="create"),
    path('remove_user_from_group/<int:user_id>/<int:tournament_group_id>/', remove_user_from_group, name="remove_user_from_group"),
    path('update/<int:pk>/', tournament_group_update_view, name="update"),
    path('update_tournament_group_title/<int:tournament_group_id>/<str:title>/', update_tournament_group_title, name="update_tournament_group_title"),
    path('view_tournament_group/<int:pk>/', view_tournament_group, name="view"),
]