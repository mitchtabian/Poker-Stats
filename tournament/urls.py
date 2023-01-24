from django.urls import include, path

from tournament.views import (
    TournamentCreateView,
    TournamentStructureCreateView,
)

app_name = 'tournament'

urlpatterns = [
    path('create_tournament', TournamentCreateView.as_view(), name="create_tournament"),
    path('create_tournament_structure', TournamentStructureCreateView.as_view(), name="create_tournament_structure"),
]