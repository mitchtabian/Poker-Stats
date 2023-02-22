from dataclasses import dataclass
import datetime
from django.utils import timezone

DID_NOT_PLACE_VALUE = 999999999

"""
A Split Elimination event for tournament timelines.
"""
@dataclass
class TournamentSplitEliminationEvent:
	eliminatee_username: str
	eliminator_usernames: list[str]
	timestamp: datetime

def build_split_elimination_event(tournament_split_elimination):
	eliminators_string = tournament_split_elimination.get_eliminators()
	eliminator_usernames = eliminators_string.split(",")
	return TournamentSplitEliminationEvent(
		eliminatee_username = tournament_split_elimination.eliminatee.user.username,
		eliminator_usernames = eliminator_usernames,
		timestamp = tournament_split_elimination.eliminated_at,
	)


"""
An Elimination event for tournament timelines.
"""
@dataclass
class TournamentEliminationEvent:
	eliminatee_username: str
	eliminator_username: str
	timestamp: datetime

def build_elimination_event(tournament_elimination):
	return TournamentEliminationEvent(
		eliminatee_username = tournament_elimination.eliminatee.user.username,
		eliminator_username = tournament_elimination.eliminator.user.username,
		timestamp = tournament_elimination.eliminated_at,
	)

"""
A Rebuy event for tournament timelines.
"""
@dataclass
class TournamentRebuyEvent:
	username: str
	timestamp: datetime

def build_rebuy_event(tournament_rebuy):
	return TournamentRebuyEvent(
		username = tournament_rebuy.player.user.username,
		timestamp = tournament_rebuy.timestamp,
	)

"""
A Completion event for tournament timelines.
"""
@dataclass
class TournamentCompleteEvent:
	winning_player_username: str
	timestamp: datetime

def build_completion_event(completed_at, winning_player):
	return TournamentCompleteEvent(
		winning_player_username = winning_player.user.username,
		timestamp = completed_at,
	)

"""
An in-progress event for tournament timelines.
"""
@dataclass
class TournamentInProgressEvent:
	in_progress_description: str
	started_at: datetime
	timestamp: datetime

def build_in_progress_event(started_at):
	in_progress_description = "The tournament is in progress!"
	return TournamentInProgressEvent(
		in_progress_description = in_progress_description,
		started_at = started_at,
		timestamp = timezone.now()
	)

"""
player_id: TournamentPlayer id.
placement: Where they placed in the tournament. 1 is considered 1st place.
"""
@dataclass
class PlayerTournamentPlacement:
	player_id: int
	placement: int

"""
A utility data holder class for modeling information used in complex views like tournament_admin_view.
player_id: TournamentPlayer pk

bounties: float b/c its possible to share an elimination between multiple players. (TournamentSplitElimination).
"""
@dataclass
class PlayerTournamentData:
	player_id: int
	username: str
	rebuys: int
	bounties: float
	is_eliminated: bool

"""
Summary eliminations data. This includes split eliminations.
"""
@dataclass
class PlayerEliminationsSummaryData:
	# id of the user who did the eliminating.
	player_id: int

	# username of the user who did the eliminating.
	player_username: int

	# Number of eliminations. Float b/c its possible to have a split elimination.
	num_eliminations: float

	# Amount earned from bounties
	bounty_earnings: float

"""
A player and all the players they eliminated. This does not include split eliminations.
"""
@dataclass
class PlayerEliminationsData:
	# id of the user who did the eliminating.
	player_id: int

	# username of the user who did the eliminating.
	player_username: int

	# username's of the players that were eliminated.
	eliminated_player_usernames: list[str]

"""
A player and all the split eliminations they were part of.
"""
@dataclass
class SplitEliminationsData:
	# ids of the users who did the eliminating.
	player_ids: list[int]

	# usernames of the users who did the eliminating.
	player_usernames: list[str]

	# username of the player who was eliminated.
	eliminated_player_username: str

def build_placement_string(placement):
	if placement == 0:
		return "1st"
	elif placement == 1:
		return "2nd"
	elif placement == 2:
		return "3rd"
	elif placement == DID_NOT_PLACE_VALUE:
		return "--"
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

"""
Builds a PlayerEliminationsSummaryData.
"""
def build_player_eliminations_summary_data_from_eliminations(eliminator, eliminations, split_eliminations):
	eliminated_usernames = []
	eliminations_count = 0.00
	for elimination in eliminations:
		eliminated_usernames.append(elimination.eliminatee.user.username)
		eliminations_count += 1.00
	for split_elimination in split_eliminations:
		eliminated_usernames.append(split_elimination.eliminatee.user.username)
		num_eliminators = len(split_elimination.eliminators.all())
		eliminations_count += 1.00 / num_eliminators
	if len(eliminated_usernames) > 0:
		bounty_amount = eliminator.tournament.tournament_structure.bounty_amount
		bounty_earnings = 0
		if bounty_amount != None:
			bounty_earnings = float(bounty_amount) * float(eliminations_count)
		data = PlayerEliminationsSummaryData(
			player_id = eliminator.id,
			player_username = eliminator.user.username,
			num_eliminations = round(eliminations_count, 2),
			bounty_earnings = bounty_earnings
		)
		return data
	return None

"""
Builds a PlayerEliminationsData.
eliminator: The TournamentPlayer who did the eliminating.
eliminations: List of TournamentElimination's for the eliminator.

Return None if they did not eliminate anyone.
"""
def build_player_eliminations_data_from_eliminations(eliminator, eliminations):
	eliminated_usernames = []
	for elimination in eliminations:
		eliminated_usernames.append(elimination.eliminatee.user.username)
	if len(eliminated_usernames) > 0:
		data = PlayerEliminationsData(
			player_id = eliminator.id,
			player_username = eliminator.user.username,
			eliminated_player_usernames = eliminated_usernames,
		)
		return data
	return None

"""
Returns a list of SplitEliminationsData.
split_eliminations: List of TournamentSplitElimination's in the entire tournament.
"""
def build_split_eliminations_data(split_eliminations):
	split_eliminations_data = []
	for elimination in split_eliminations:
		eliminators = elimination.eliminators.all()
		player_ids = [eliminator.id for eliminator in eliminators]
		player_usernames = [eliminator.user.username for eliminator in eliminators]
		eliminated_player_username = elimination.eliminatee.user.username
		data = SplitEliminationsData(
			player_ids = player_ids,
			player_usernames = player_usernames,
			eliminated_player_username = eliminated_player_username,
		)
		split_eliminations_data.append(data)
	return split_eliminations_data

def get_tournament_started_at(tournament):
	if tournament.started_at != None:
		return tournament.started_at
	else:
		return timezone.now()























