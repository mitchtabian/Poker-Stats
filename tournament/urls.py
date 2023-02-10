from django.urls import include, path

from tournament.views import (
    complete_tournament,
    eliminate_player_from_tournament,
    invite_player_to_tournament,
    get_tournament_structure,
    join_tournament,
    rebuy_player_in_tournament,
    remove_player_from_tournament,
    start_tournament,
    tournament_admin_view,
    tournament_create_view,
    tournament_edit_view,
    tournament_list_view,
    tournament_structure_create_view,
    tournament_view,
    undo_completed_at,
    undo_started_at,
    uninvite_player_from_tournament,
)

app_name = 'tournament'

urlpatterns = [
    path('complete/<int:pk>/', complete_tournament, name="complete"),
    path('create_tournament/', tournament_create_view, name="create_tournament"),
    path('create_tournament_structure/', tournament_structure_create_view, name="create_tournament_structure"),
    path('eliminate_player/<int:tournament_id>/<int:eliminator_id>/<int:eliminatee_id>/', eliminate_player_from_tournament, name="eliminate_player"),
    path('invite_player_to_tournament/<int:player_id>/<int:tournament_id>/', invite_player_to_tournament, name="invite_player"),
    path('get_tournament_structure/', get_tournament_structure, name="get_tournament_structure"),
    path('join_tournament/<int:pk>/', join_tournament, name="join_tournament"),
    path('player_rebuy/<int:player_id>/<int:tournament_id>/', rebuy_player_in_tournament, name="player_rebuy"),
    path('remove_player/<int:player_id>/<int:tournament_id>/', remove_player_from_tournament, name="remove_player"),
    path('start/<int:pk>/', start_tournament, name="start"),
    path('tournament_admin_view/<int:pk>/', tournament_admin_view, name="tournament_admin_view"),
    path('tournament_edit/<int:pk>/', tournament_edit_view, name="tournament_edit"),
    path('tournament_list/<int:pk>/', tournament_list_view, name="tournament_list"),
    path('tournament_view/<int:pk>/', tournament_view, name="tournament_view"),
    path('undo_complete/<int:pk>/', undo_completed_at, name="undo_complete"),
    path('undo_started/<int:pk>/', undo_started_at, name="undo_started"),
    path('uninvite/<int:player_id>/<int:tournament_id>/', uninvite_player_from_tournament, name="uninvite"),
]



