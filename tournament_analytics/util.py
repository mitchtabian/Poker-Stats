from django.contrib.humanize.templatetags.humanize import naturalday
from django.utils import timezone
from decimal import Decimal
import json
import random

from tournament.models import (
	TournamentPlayerResult,
	TournamentElimination,
	TournamentSplitElimination,
	TournamentRebuy
)
from tournament.util import get_value_or_default

def build_json_from_tournament_totals_data(list_of_tournament_totals):
	data_list = []
	for item in list_of_tournament_totals:
		data = {
			'timestamp': naturalday(item.timestamp),
			'net_earnings': f"{item.net_earnings}",
			'losses': f"{item.losses}",
			'gross_earnings': f"{item.gross_earnings}"
		}
		data_list.append(data)
	return json.dumps(data_list)

"""
Build json of TournamentPlayerResult data for each tournament.
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
				'net_earnings': f"{result.net_earnings}",
				'gross_earnings': f"{result.gross_earnings}",
				'tournament_title': result.tournament.title,
				'completed_at': naturalday(result.tournament.completed_at),
				'eliminations': f"{round(Decimal(len(eliminations) + split_eliminations_count), 2)}",
				'rebuys': len(rebuys),
				'losses': f"{result.investment}",
			}
	return json.dumps(tournament_players_result_dict)

"""
Build json of eliminations on per-user basis. In otherwords, how many times you eliminated each player.

The json object also contains a color for each player they eliminatied. This is for chart coloring.

[
	{
		"username": "<username1>",
		"count": <elim_count>,
		"color": <rgbcolor>
	},
	{
		"username": "<username2>",
		"count": <elim_count>,
		"color": <rgbcolor>
	},
	...
]
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
			split_eliminations_count = 0
			for split_elimination in split_eliminations:
				split_eliminations_count += 1.00 / len(split_elimination.eliminators.all())
				if f"{split_elimination.eliminatee.user.username}" in eliminations_dict:
					eliminations_dict[f"{split_elimination.eliminatee.user.username}"] += split_eliminations_count
				else:
					eliminations_dict[f"{split_elimination.eliminatee.user.username}"] = split_eliminations_count

	eliminations = []
	for username_key in eliminations_dict.keys():
		elim_count = eliminations_dict[username_key]
		color_list = list(random.choices(range(256), k=3))
		color = f"rgb({color_list[0]}, {color_list[1]}, {color_list[2]})"
		item = {
			'username': username_key,
			'short_username': shorten_string(username_key, 15),
			'count': elim_count,
			'color': color
		}
		eliminations.append(item)

	eliminations = sorted(
		eliminations,
		key = lambda x: x['count'],
		reverse = True
	)
	return json.dumps(eliminations)


def shorten_string(string, length):
	if len(string) > length:
		return f"{string[:length]}..."
	return string


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
				'eliminations': f"{round(Decimal(len(eliminations) + split_eliminations_count), 2)}",
				'rebuys': len(rebuys),
				'tournament_title': player.tournament.title,
				'completed_at': naturalday(player.tournament.completed_at)
			}
	return json.dumps(rebuys_and_eliminations_dict)


















