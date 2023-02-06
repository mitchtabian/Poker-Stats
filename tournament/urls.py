from django.urls import include, path

from tournament.views import (
    complete_tournament,
    start_tournament,
    tournament_create_view,
    tournament_edit_view,
    tournament_list_view,
    tournament_structure_create_view,
    tournament_view,
    undo_completed_at,
)

app_name = 'tournament'

urlpatterns = [
    path('complete/<int:pk>/', complete_tournament, name="complete"),
    path('create_tournament/', tournament_create_view, name="create_tournament"),
    path('create_tournament_structure/', tournament_structure_create_view, name="create_tournament_structure"),
    path('tournament_edit/<int:pk>/', tournament_edit_view, name="tournament_edit"),
    path('tournament_list/<int:pk>/', tournament_list_view, name="tournament_list"),
    path('start/<int:pk>/', start_tournament, name="start"),
    path('tournament_view/<int:pk>/', tournament_view, name="tournament_view"),
    path('undo_complete/<int:pk>/', undo_completed_at, name="undo_complete"),
]