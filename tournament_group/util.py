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















