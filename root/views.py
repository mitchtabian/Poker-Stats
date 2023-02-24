from django.contrib import messages
from django.shortcuts import render, redirect, reverse
from django.utils import timezone
from decimal import Decimal
import random

from tournament.models import (
	TournamentInvite,
	TournamentPlayer,
	TournamentState,
	TournamentElimination,
	TournamentRebuy,
	TournamentSplitElimination,
	TournamentPlayerResult
)
from tournament_analytics.models import TournamentTotals
from tournament_analytics.util import something

from tournament.util import get_value_or_default

def root_view(request):
	try:
		user = request.user
		context = {}
		if user.is_authenticated:
			invites = TournamentInvite.objects.find_pending_invites_for_user(user.id)
			for invite in invites:
				if invite.tournament.get_state() == TournamentState.COMPLETED:
					invites = invites.exclude(tournament=invite.tournament)
			context['invites'] = invites

			# get all the Tournaments that this user has joined
			tournament_players = TournamentPlayer.objects.get_all_tournament_players_by_user_id(user.id)
			tournaments = []
			for player in tournament_players:
				tournaments.append(player.tournament)
			context['tournaments'] = tournaments

			# Get TournamentTotals data
			tournament_totals = TournamentTotals.objects.get_or_build_tournament_totals_by_user_id(user_id = user.id)
			tournament_totals = sorted(tournament_totals, key=lambda x: x.timestamp, reverse=False)
			context['tournament_totals'] = tournament_totals

			# Build rebuys and eliminations graph data
			rebuys_and_eliminations_dict = build_rebuys_and_eliminations_data(tournament_players)
			if rebuys_and_eliminations_dict:
				context['rebuys_and_eliminations'] = rebuys_and_eliminations_dict

			# Build the TournamentPlayerResult graph data
			tournament_player_results_dict = build_tournament_player_result_data(tournament_players)
			if tournament_player_results_dict:
				context['tournament_player_results'] = tournament_player_results_dict
				context['tournament_title_length'] = something(tournament_player_results_dict)

			# Build eliminations for each player (bar graph).
			# Contains how many times you eliminated each player.
			player_eliminations_dict = build_player_eliminations_data(tournament_players)
			if player_eliminations_dict:
				context['eliminations_dict'] = player_eliminations_dict

				# For each player they eliminated, generate a random color for the graph
				colors = []
				for x in player_eliminations_dict:
					color_list = list(random.choices(range(256), k=3))
					color = f"rgb({color_list[0]}, {color_list[1]}, {color_list[2]})"
					colors.append(color)
				context['elimination_colors'] = colors

			return render(request, "root/root.html", context=context)
		else:
			return redirect("/accounts/login/")
	except Exception as e:
		messages.error(request, e.args[0])
		return render(request, "root/root.html", context={})

"""
Build dictionary of eliminations on per-user basis. In otherwords, how many times you eliminated each player.
"""
def build_player_eliminations_data(players):
	eliminations_dict = {}
	for player in players:
		if player.tournament.completed_at != None:
			# Get all the eliminations where this player was the eliminator
			eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
				player_id = player.id
			)
			for elimination in eliminations:
				if f"{elimination.eliminatee.user.username}" in eliminations_dict:
					eliminations_dict[f"{elimination.eliminatee.user.username}"] += 1
				else:
					eliminations_dict[f"{elimination.eliminatee.user.username}"] = 1

			# Get all the split eliminations where this player was one of the eliminators
			split_eliminations = TournamentSplitElimination.objects.get_split_eliminations_by_eliminator(
				player_id = player.id
			)
			for split_elimination in split_eliminations:
				split_eliminations_count += 1.00 / len(split_elimination.eliminators.all())
				if f"{split_eliminations_count.eliminatee.user.username}" in eliminations_dict:
					eliminations_dict[f"{split_eliminations_count.eliminatee.user.username}"] += split_eliminations_count
				else:
					eliminations_dict[f"{split_eliminations_count.eliminatee.user.username}"] = split_eliminations_count
	return eliminations_dict


"""
Build dictionary of TournamentPlayerResult data for each tournament.
"""
def build_tournament_player_result_data(players):
	# Sort from oldest tournament to newest
	tournament_players = sorted(
		players,
		key=lambda x: get_value_or_default(x.tournament.completed_at, timezone.now()),reverse=False
	)
	tournament_players_result_dict = {}
	for player in tournament_players:
		if player.tournament.completed_at != None:
			result = TournamentPlayerResult.objects.get_results_for_user_by_tournament(
				tournament_id = player.tournament.id,
				user_id = player.user.id
			)[0]
			eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
				player_id = player.id
			)
			split_eliminations = TournamentSplitElimination.objects.get_split_eliminations_by_eliminator(
				player_id = player.id
			)
			split_eliminations_count = 0
			for split_elimination in split_eliminations:
				eliminators = split_elimination.eliminators.all()
				split_eliminations_count += 1.00 / len(eliminators)
			rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			tournament_players_result_dict[f"{player.tournament.completed_at}"] = {
				'placement': result.placement,
				'net_earnings': result.net_earnings,
				'gross_earnings': result.gross_earnings,
				'tournament_title': result.tournament.title,
				'completed_at': result.tournament.completed_at,
				'eliminations': round(Decimal(len(eliminations) + split_eliminations_count), 2),
				'rebuys': len(rebuys),
				'losses': result.investment,
			}
	return tournament_players_result_dict



"""
Build a dictionary of the rebuys, eliminations and split eliminations data.

"""
def build_rebuys_and_eliminations_data(players):
	# Sort from oldest tournament to newest
	tournament_players = sorted(
		players,
		key=lambda x: get_value_or_default(x.tournament.completed_at, timezone.now()),reverse=False
	)
	rebuys_and_eliminations_dict = {}
	for player in tournament_players:
		if player.tournament.completed_at != None:
			eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
				player_id = player.id
			)
			split_eliminations = TournamentSplitElimination.objects.get_split_eliminations_by_eliminator(
				player_id = player.id
			)
			split_eliminations_count = 0
			for split_elimination in split_eliminations:
				eliminators = split_elimination.eliminators.all()
				split_eliminations_count += 1.00 / len(eliminators)
			rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			rebuys_and_eliminations_dict[f"{player.tournament.completed_at}"] = {
				'eliminations': round(Decimal(len(eliminations) + split_eliminations_count), 2),
				'rebuys': len(rebuys),
				'tournament_title': player.tournament.title,
				'completed_at': player.tournament.completed_at
			}
	return rebuys_and_eliminations_dict

def contact_view(request):
	return render(request, "root/contact.html")

def error_view(request, *args, **kwargs):
	message = kwargs['error_message']
	context = {}
	context['message'] = message
	return render(request=request, template_name="root/error.html", context=context)








