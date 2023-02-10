from dataclasses import dataclass

"""
A utility data holder class for modeling information used in complex views like tournament_admin_view.
"""
@dataclass
class PlayerTournamentData:
	user_id: int
	username: str
	rebuys: int
	bounties: int
	is_eliminated: bool

def build_placement_string(placement):
	if placement == 0:
		return "1st"
	elif placement == 1:
		return "2nd"
	elif placement == 2:
		return "3rd"
	else:
		return f"{placement + 1}th"

"""
Used in a template to apply styling based on placement.

input: [Decimal(60), Decimal(30), Decimal(20)]
output: "1, 2, 3"
"""
def payout_positions(percentages):
	placements = ""
	for i in range(0, len(percentages)):
		placements += f"{i}"
		if i != len(percentages):
			placements += ","
	return placements