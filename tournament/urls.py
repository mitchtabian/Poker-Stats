from django.urls import include, path

from tournament.views import (
    TournamentCreateView,
    tournament_structure_create_view,
)

app_name = 'tournament'

urlpatterns = [
    path('create_tournament', TournamentCreateView.as_view(), name="create_tournament"),
    path('create_tournament_structure', tournament_structure_create_view, name="create_tournament_structure"),
]