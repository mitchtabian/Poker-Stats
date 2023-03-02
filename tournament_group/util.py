from dataclasses import dataclass
import json

@dataclass
class TournamentGroupNetEarnings:
	username: str
	net_earnings: float

def build_json_from_net_earnings_data(list_of_group_net_earnings):
	data_list = []
	for item in list_of_group_net_earnings:
		data = {
			'username': item.username,
			'net_earnings': f"{item.net_earnings}"
		}
		data_list.append(data)
	return json.dumps(data_list)

@dataclass
class TournamentGroupPotContributions:
	username: str
	contribution: float

def build_json_from_pot_contributions_data(list_of_group_pot_contributions):
	data_list = []
	for item in list_of_group_pot_contributions:
		data = {
			'username': item.username,
			'contribution': f"{item.contribution}"
		}
		data_list.append(data)
	return json.dumps(data_list)

@dataclass
class TournamentGroupEliminationsAndRebuys:
	username: str
	eliminations: float
	rebuys: int

def build_json_from_eliminations_and_rebuys_data(list_of_group_eliminations_and_rebuys):
	data_list = []
	for item in list_of_group_eliminations_and_rebuys:
		data = {
			'username': item.username,
			'eliminations': f"{item.eliminations}",
			'rebuys': f"{item.rebuys}"
		}
		data_list.append(data)
	return json.dumps(data_list)

@dataclass
class TournamentGroupTournamentsPlayed:
	username: str
	count: int

def build_json_from_tournaments_played_data(list_of_group_tournaments_played):
	data_list = []
	for item in list_of_group_tournaments_played:
		data = {
			'username': item.username,
			'count': f"{item.count}",
		}
		data_list.append(data)
	return json.dumps(data_list)






















