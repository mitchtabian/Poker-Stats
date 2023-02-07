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