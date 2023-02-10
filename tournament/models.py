import json
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from enum import Enum

from user.models import User

PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(100)]

from tournament.util import build_placement_string


"""
Checks if
(1) the payout_percentages sum to 100
(2) every value in payout_percentages is between 0 and 100.
"""
def validate_percentages(payout_percentages):
	total = 0
	for pct in payout_percentages:
		if pct > 100 or pct < 0:
			raise ValidationError("Each payout percentage must be between 0 and 100.")
		total += pct
	if total != 100:
		raise ValidationError("Payout Percentages must sum to 100")
	
class TournamentStructureManager(models.Manager):

	# USED FOR TESTING ONLY... create new fn using the USER instead of user_email.
	# from tournament.models import TournamentStructure
	# TournamentStructure.objects.create_tournament_struture_test("mitchs tournmanet structure", "mitch@tabian.ca", 60, 10, (70,20,10), True)
	def create_tournament_struture_test(self, title, user_email, buyin_amount, bounty_amount, payout_percentages, allow_rebuys):
		user = User.objects.get_by_email(user_email)
		validate_percentages(payout_percentages)
		tournament_structure = self.model(
			title=title,
			user=user,
			buyin_amount=buyin_amount,
			bounty_amount=bounty_amount,
			payout_percentages=payout_percentages,
			allow_rebuys=allow_rebuys
		)
		tournament_structure.save(using=self._db)
		return tournament_structure

	def create_tournament_struture(self, title, user, buyin_amount, bounty_amount, payout_percentages, allow_rebuys):
		validate_percentages(payout_percentages)
		tournament_structure = self.model(
			title=title,
			user=user,
			buyin_amount=buyin_amount,
			bounty_amount=bounty_amount,
			payout_percentages=payout_percentages,
			allow_rebuys=allow_rebuys
		)
		tournament_structure.save(using=self._db)
		return tournament_structure

	# ONLY USE FOR TESTING
	def get_structures_by_user_email(self, user_email):
		user = User.objects.get_by_email(user_email)
		structures = super().get_queryset().filter(user=user)
		return structures

	def get_structures_by_user(self, user):
		structures = super().get_queryset().filter(user=user)
		return structures

	def get_by_id(self, id):
		try:
			structure = self.get(pk=id)
		except TournamentStructure.DoesNotExist:
			structure = None
		return structure

"""
Note: buyin_amount already takes into account the bounty_amount. 
Ex: If buyin_amount=60 and bounty_amount=10, the total amount a user must pay to play is 60.
"""
class TournamentStructure(models.Model):
	title 					= models.CharField(max_length=254, blank=False, null=False)

	# The user that created this tournament structure.
	user 					= models.ForeignKey(User, on_delete=models.CASCADE)

	# Cost to buy into this tournament.
	buyin_amount			= models.DecimalField(max_digits=9, decimal_places=2, blank=False, null=False)

	# Optional. Not all tournaments must have bounties. If this is null, it is not a bounty tournament.
	bounty_amount			= models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
	
	"""
	Ex: (70, 20, 10)
	"""
	payout_percentages		= ArrayField(
								models.DecimalField(
									max_digits=3,
									decimal_places=0,
									default=0,
									validators=PERCENTAGE_VALIDATOR
								),
								validators=[validate_percentages]
							)
	allow_rebuys 			= models.BooleanField(default=False)


	objects = TournamentStructureManager()

	def __str__(self):
		return self.title

	def is_bounty_tournament(self):
		if self.bounty_amount != None:
			return True
		else:
			return False

	"""
	Builds a JSON representations of a TournamentStructure.
	"""
	def buildJson(self):
		data = {}
		data['pk'] = self.pk
		data['title'] = self.title
		data['buyin_amount'] = f"{self.buyin_amount}"
		if self.bounty_amount != None:
			data['bounty_amount'] = f"{self.bounty_amount}"
		payout_percentages = []
		for pct in self.payout_percentages:
			payout_percentages.append(f"{pct}")
		data['payout_percentages'] = payout_percentages
		return json.dumps(data)

class TournamentManager(models.Manager):

	def create_tournament(self, title, user, tournament_structure):
		if tournament_structure.user != user:
			raise ValidationError("You cannot use a Tournament Structure that you don't own.")
		tournament = self.model(
			title=title,
			admin=user,
			tournament_structure=tournament_structure
		)
		tournament.save(using=self._db)

		# The admin automatically becomes a player in the tournament
		player = TournamentPlayer.objects.create_player_for_tournament(
			user_id = user.id,
			tournament_id = tournament.id	
		)

		return tournament

	# Tournament.objects.complete_tournament(user, 1)
	def complete_tournament(self, user, tournament_id):
		tournament = self.get(pk=tournament_id)
		if tournament.admin != user:
			raise ValidationError("You cannot update a Tournament if you're not the admin.")
		if tournament.started_at is None:
			raise ValidationError("You can't complete a Tournament that has not been started.")
		if tournament.completed_at is not None:
			raise ValidationError("This tournament is already completed.")

		# Verify every player except 1 has been eliminated. This will raise if false.
		self.is_completable(tournament_id)

		tournament.completed_at = timezone.now()
		tournament.save(using=self._db)

		# Calculate the TournamentPlayerResultData for each player. These are saved to db.
		results = TournamentPlayerResult.objects.build_results_for_tournament(tournament_id)

		return tournament

	"""
	Undo tournament completion.
	When you do this, all the elimations and rebuys data is deleted. Essentially you start a blank slate.
	"""
	def undo_complete_tournament(self, user, tournament_id):
		tournament = self.get(pk=tournament_id)
		if tournament.admin != user:
			raise ValidationError("You cannot update a Tournament if you're not the admin.")
		if tournament.completed_at is None:
			raise ValidationError("The tournament is not completed. Nothing to undo.")

		# Delete all eliminations
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(tournament_id)
		for elimination in eliminations:
			elimination.delete()

		# Delete all the rebuy data
		players = TournamentPlayer.objects.get_tournament_players(tournament_id)
		for player in players:
			player.num_rebuys = 0
			player.save(using=self._db)

		tournament.completed_at = None
		tournament.save(using=self._db)

		# Delete any Tournament results.
		TournamentPlayerResult.objects.delete_results_for_tournament(tournament_id)

		return tournament

	# Tournament.objects.start_tournament(user, 1)
	def start_tournament(self, user, tournament_id):
		tournament = self.get(pk=tournament_id)
		if tournament.admin != user:
			raise ValidationError("You cannot update a Tournament if you're not the admin.")
		if tournament.completed_at is not None:
			raise ValidationError("You can't start a Tournament that has already been completed.")
		tournament.started_at = timezone.now()
		tournament.save(using=self._db)
		return tournament

	def get_by_id(self, tournament_id):
		try:
			tournament = self.get(pk=tournament_id)
		except Tournament.DoesNotExist:
			tournament = None
		return tournament

	def get_by_user(self, user):
		tournaments = super().get_queryset().filter(admin=user)
		return tournaments

	"""
	A Tournament is completable if every player except 1 has been completely eliminated.
	Meaning, all players have no remaining rebuys.

	If players remain, raise ValidationError.

	If only 1 player remains, return True.
	"""
	def is_completable(self, tournament_id):
		tournament = self.get_by_id(tournament_id)
		players = TournamentPlayer.objects.get_tournament_players(tournament_id)
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(tournament_id)

		# sum buyins + rebuys
		total_buyins = 0
		for player in players:
			total_buyins += 1
			total_buyins += player.num_rebuys

		# Find the number of eliminations
		total_eliminations = len(eliminations)

		# If every play is eliminated, the difference will be 1
		if total_buyins - total_eliminations != 1:
			raise ValidationError("Every player must be eliminated before completing a Tournament")
		return True

	"""
	Calculate the total value of a particular Tournament.
	Value cannot be calculated until a Tournament is complete.
	"""
	def calculate_tournament_value(self, tournament_id, num_rebuys):
		tournament = Tournament.objects.get_by_id(tournament_id)
		if tournament.completed_at == None:
			raise ValidationError("Tournament value cannot be calculated until a Tournament is complete.")
		buyin_amount = tournament.tournament_structure.buyin_amount
		# Sum the initial buyin amounts
		players = TournamentPlayer.objects.get_tournament_players(tournament_id)
		total_tournament_value = buyin_amount * len(players)
		# Add amount from rebuys
		total_tournament_value += buyin_amount * num_rebuys
		return round(Decimal(total_tournament_value), 2)

"""
The states a tournament can be in.
INACTIVE: started_at == None and completed_at == None.
ACTIVE: started_at != None and completed_at == None.
COMPLETED: started_at != None and complated_at != None.
"""
class TournamentState(Enum):
	INACTIVE = 0
	ACTIVE = 1
	COMPLETED = 2

class Tournament(models.Model):
	title 					= models.CharField(max_length=254, blank=False, null=False)
	admin					= models.ForeignKey(User, on_delete=models.CASCADE)
	tournament_structure	= models.ForeignKey(TournamentStructure, on_delete=models.CASCADE)

	# Set once the tournament has started.
	started_at				= models.DateTimeField(null=True, blank=True)

	# Set once the tournament has finished.
	completed_at			= models.DateTimeField(null=True, blank=True)

	objects = TournamentManager()

	def __str__(self):
		return self.title

	def get_state(self):
		if self.started_at == None and self.completed_at == None:
			return TournamentState.INACTIVE
		if self.started_at != None and self.completed_at == None:
			return TournamentState.ACTIVE 
		if self.started_at != None and self.completed_at != None:
			return TournamentState.COMPLETED

	def get_state_string(self):
		if self.get_state() == TournamentState.INACTIVE:
			return "INACTIVE"
		if self.get_state() == TournamentState.ACTIVE:
			return "ACTIVE"
		if self.get_state() == TournamentState.COMPLETED:
			return "COMPLETED"

class TournamentPlayerManager(models.Manager):

	# from tournament.models import TournamentPlayer
	# TournamentPlayer.objects.create_player_for_tournament(user.id, tourament.id)
	def create_player_for_tournament(self, user_id, tournament_id):
		added_user = User.objects.get_by_id(user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)

		if tournament.completed_at != None:
			raise ValidationError("You can't add players to a Tournment that is completed.")

		if tournament.started_at != None:
			raise ValidationError("You can't add players to a Tournment that is started.")

		player = self.get_tournament_player_by_user_id(added_user.id, tournament_id)

		# This player is already added to this tournament
		if player != None:
			raise ValidationError(f"{added_user.username} is already added to this tournament.")

		# This player has not been added to the tournament - add them.
		player = self.model(
			user=added_user,
			tournament=tournament
		)
		player.save(using=self._db)

		# Delete the invite
		invites = TournamentInvite.objects.find_pending_invites(
			send_to_user_id = added_user.id,
			tournament_id = tournament.id
		)
		# There should only be one invite but delete them all since its a queryset
		for invite in invites:
			invite.delete()

		return player

	def remove_player_from_tournament(self, removed_by_user_id, removed_user_id, tournament_id):
		removed_by_user = User.objects.get_by_id(removed_by_user_id)
		removed_user = User.objects.get_by_id(removed_user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)

		player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			user_id = removed_user.id,
			tournament_id = tournament_id
		)

		if tournament.admin == player.user:
			raise ValidationError("The admin cannot be removed from a Tournament.")

		if tournament.admin != removed_by_user and player.id != player_id:
			raise ValidationError("Only the admin can remove players.")

		if tournament.completed_at != None:
			raise ValidationError("You can't remove players from a Tournment that is completed.")

		if tournament.started_at != None:
			raise ValidationError("You can't remove players from a Tournment that is started.")

		player.delete()


	# from tournament.models import TournamentPlayer
	# TournamentPlayer.objects.get_tournament_player(user.id, tourament.id)
	"""
	If the query returns multiple players, the tournament is corrupt - multiple instances of the same player
	have been added. Attempt to fix by removing them. The player will have to be re-added.

	If the query returns a single list item, return that player.

	If the query returns no results, return None.
	"""
	def get_tournament_player_by_user_id(self, user_id, tournament_id):
		user = User.objects.get_by_id(user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)
		players = super().get_queryset().filter(user=user, tournament=tournament)
		if len(players) > 1:
			for player in players:
				player.delete()
			raise ValidationError("This tournament is corrupt. The same user has been added multiple times.  Attempting to fix...")
		
		if len(players) == 1:
			return players.first()
		else:
			return None

	"""
	Get all the TournamentPlayers for this tournament.
	"""
	def get_tournament_players(self, tournament_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		players = super().get_queryset().filter(tournament=tournament).order_by("user__username")
		return players

	"""
	Get all the TournamentPlayers for this player.
	"""
	def get_all_tournament_players_by_user_id(self, user_id):
		user = User.objects.get_by_id(user_id)
		players = super().get_queryset().filter(user=user)
		return players

	"""
	A player has re-bought.
	Increment num_rebuys.

	Make sure not to increment num_rebuys if they're not out of rebuys.
	Basically don't let them rebuy unless they're eliminated.
	"""
	def rebuy_by_user_id_and_tournament_id(self, user_id, tournament_id):
		user = User.objects.get_by_id(user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)
		tournament_player = TournamentPlayer.objects.get_tournament_player_by_user_id(user_id, tournament_id)

		# Verify the tournament allows rebuys
		if not tournament.tournament_structure.allow_rebuys:
			raise ValidationError("This tournament does not allow rebuys. Update the Tournament Structure.")

		# Verify they're out of rebuys.
		num_eliminations = len(
			TournamentElimination.objects.get_eliminations_by_tournament(
				tournament_id
			).filter(eliminatee=user)
		)
		if num_eliminations <= tournament_player.num_rebuys:
			raise ValidationError(
				f"{tournament_player.user.username} still has an active rebuy. Eliminate them before adding another rebuy."
			)
		tournament_player.num_rebuys += 1
		tournament_player.save(using=self._db)
		return tournament_player

"""
A player associated with specific tournament.
"""
class TournamentPlayer(models.Model):
	user					= models.ForeignKey(User, on_delete=models.CASCADE)	
	tournament				= models.ForeignKey(Tournament, on_delete=models.CASCADE)
	num_rebuys				= models.IntegerField(
								default=0,
								validators=[
									MaxValueValidator(100),
									MinValueValidator(0)
								]
							)
	
	objects = TournamentPlayerManager()

	def __str__(self):
		return self.user.username

class TournamentInviteManager(models.Manager):
	
	# Send a tournament invite to a user. When they accept, they will become a TournamentPlayer.
	def send_invite(self, sent_from_user_id, send_to_user_id, tournament_id):
		try:
			send_to = User.objects.get_by_id(send_to_user_id)
			sent_from = User.objects.get_by_id(sent_from_user_id)
			try:
				tournament = Tournament.objects.get_by_id(tournament_id)

				# Verify the person sending the invite is the tournament admin
				if tournament.admin != sent_from:
					raise ValidationError("You can't send invites unless you're the admin.")

				# Verify the admin is not inviting themself to the tournament
				if tournament.admin == send_to:
					raise ValidationError("You can't invite yourself to the Tournament.")

				# Verify the Tournament isn't completed
				if tournament.get_state() == TournamentState.COMPLETED:
					raise ValidationError("You can't invite to a Tournment that's completed.")

				# Verify the Tournament isn't started
				if tournament.get_state() == TournamentState.ACTIVE:
					raise ValidationError("You can't invite to a Tournment that's started.")

				# Verify there isn't already a pending invite.
				pending_invite = TournamentInvite.objects.find_pending_invites(send_to.id, tournament.id)
				if len(pending_invite) > 0:
					raise ValidationError(f"{send_to.username} has already been invited.")

				# Verify this user isn't already a player in this tournament
				player = TournamentPlayer.objects.get_tournament_player_by_user_id(
					user_id = send_to.id,
					tournament_id = tournament.id
				)
				if player != None:
					raise ValidationError(f"{send_to.username} is already in this tournament.")

				if len(pending_invite) > 0:
					raise ValidationError(f"{send_to.username} has already been invited.")

				invite = self.model(
					send_to=send_to,
					tournament=tournament
				)
				invite.save(using=self._db)
				return invite
			except Tournament.DoesNotExist:
				raise ValidationError("The tournament you're inviting to doesn't exist.")
		except User.DoesNotExist:
			raise ValidationError("The user you're inviting doesn't exist.")

	def uninvite_player_from_tournament(self, admin, uninvite_user_id, tournament_id):
		admin = User.objects.get_by_id(admin)
		uninvite_user = User.objects.get_by_id(uninvite_user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)

		# Verify the person removing the invite is the tournament admin
		if tournament.admin != admin:
			raise ValidationError("You can't remove invites unless you're the admin.")

		invites = TournamentInvite.objects.find_pending_invites(
			send_to_user_id=uninvite_user.id,
			tournament_id=tournament_id
		)

		if len(invites) == 0:
			raise ValidationError("That player does not have an invition to this tournament.")

		# There should only be one, but just in case we'll loop
		for invite in invites:
			invite.delete()



	# Return a queryset containing any pending invites for a user and a tournament.
	def find_pending_invites(self, send_to_user_id, tournament_id):
		send_to = User.objects.get_by_id(send_to_user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)
		invites = super().get_queryset().filter(send_to=send_to, tournament=tournament)
		return invites

	def find_pending_invites_for_user(self, send_to_user_id):
		send_to = User.objects.get_by_id(send_to_user_id)
		invites = super().get_queryset().filter(send_to=send_to)
		return invites

	def find_pending_invites_for_tournament(self, tournament_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		invites = super().get_queryset().filter(tournament=tournament)
		return invites

class TournamentInvite(models.Model):
	send_to 				= models.ForeignKey(User, on_delete=models.CASCADE)
	tournament 				= models.ForeignKey(Tournament, on_delete=models.CASCADE)

	objects = TournamentInviteManager()

	def __str__(self):
		return f"Invite for tournament {self.tournament.title} sent to {self.send_to.username}."



class TournamentEliminationManager(models.Manager):
	def get_eliminations_by_tournament(self, tournament_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		eliminations = super().get_queryset().filter(
			tournament=tournament,
		)
		return eliminations

	def get_eliminations_by_eliminator(self, tournament_id, eliminator_id):
		eliminator = User.objects.get_by_id(eliminator_id)
		tournament = Tournament.objects.get_by_id(tournament_id)
		eliminations = super().get_queryset().filter(
			tournament=tournament,
			eliminator=eliminator,
		)
		return eliminations

	def create_elimination(self, tournament_id, eliminator_id, eliminatee_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		eliminator = User.objects.get_by_id(eliminator_id)
		eliminatee = User.objects.get_by_id(eliminatee_id)

		# Verify the Tournament has started
		if tournament.get_state() != TournamentState.ACTIVE:
			raise ValidationError("You can only eliminate players if the Tournament is Active.")
		
		# Make sure a player isn't trying to eliminate themself.
		if eliminator == eliminatee:
			raise ValueError(f"{eliminator.username} can't eliminate themselves!")

		# Verify these players are part of this tournament.
		tournament_users = list(
			map(lambda tp: tp.user, TournamentPlayer.objects.get_tournament_players(tournament_id))
		)
		if eliminator not in tournament_users:
			raise ValidationError(f"{eliminator.username} is not part of this tournament.")
		if eliminatee not in tournament_users:
			raise ValidationError(f"{eliminatee.username} is not part of this tournament.")

		# Verify this is not the last player in the Tournament.
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		num_rebuys = 0
		if tournament.tournament_structure.allow_rebuys:
			for player in players:
				num_rebuys += player.num_rebuys
		total_buyins = num_rebuys + len(players)
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(
			tournament_id = tournament.id
		)
		if total_buyins <= (len(eliminations) + 1):
			raise ValidationError("You can't eliminate any more players. Complete the Tournament.")

		# Verify a multiple-eliminations aren't happening unless they've rebought.
		is_player_eliminated = self.is_player_eliminated(
			user_id = eliminatee.id,
			tournament_id = tournament_id
		)
		if is_player_eliminated:
			raise ValidationError(f"{eliminatee.username} has already been eliminated and has no more re-buys.")

		elimination = self.model(
			tournament=tournament,
			eliminator=eliminator,
			eliminatee=eliminatee
		)
		elimination.save(using=self._db)
		return elimination

	"""
	Return True is a player has been eliminated from a Tournament (and has no more rebuys).
	How?
	Compare the number of times they've been eliminated against the number of rebuys.
	Remember: If they've rebought once they will have one existing elimination.
	"""
	def is_player_eliminated(self, user_id, tournament_id):
		existing_eliminations = self.get_eliminations_by_tournament(tournament_id)
		player_eliminations = 0
		tournament_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			user_id=user_id,
			tournament_id=tournament_id,
		)
		for elimination in existing_eliminations:
			if elimination.eliminatee.id == user_id:
				player_eliminations += 1
			if player_eliminations > 0:
				if player_eliminations > tournament_player.num_rebuys:
					return True
		return False


"""
Tracks the data for eliminations. 

eliminator: Person who did the eliminating.

eliminatee: Person who got eliminated.

eliminated_at: When they were eliminated. This is used to calculate placements.
"""
class TournamentElimination(models.Model):
	tournament				= models.ForeignKey(Tournament, on_delete=models.CASCADE)
	eliminator				= models.ForeignKey(User, related_name="Eliminator", on_delete=models.CASCADE)	
	eliminatee				= models.ForeignKey(User, related_name="Eliminatee", on_delete=models.CASCADE)
	eliminated_at			= models.DateTimeField(auto_now_add=True)
	
	objects = TournamentEliminationManager()

	def __str__(self):
		return f"{self.eliminator.username} eliminated {self.eliminatee.username}."


class TournamentPlayerResultManager(models.Manager):

	def get_results_for_tournament(self, tournament_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		return super().get_queryset().filter(tournament=tournament)

	def get_results_for_user_by_tournament(self, user_id, tournament_id):
		player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament_id,
			user_id = user_id,
		)
		tournament = Tournament.objects.get_by_id(tournament_id)
		return super().get_queryset().filter(tournament=tournament, player=player)

	def delete_results_for_tournament(self, tournament_id):
		results = self.get_results_for_tournament(tournament_id)
		for result in results:
			result.delete()

	def build_results_for_tournament(self, tournament_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		if tournament.completed_at == None:
			raise ValidationError("You cannot build Tournament results until the Tournament is complete.")
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament_id
		)
		results = []
		for player in players:
			result = self.create_tournament_player_result(
				user_id = player.user.id,
				tournament_id = tournament_id
			)
			results.append(result)
		return results

	"""
	Determine what a player placed in a tournament.
	Note: This is -1 indexed! So whoever came first will have placement = 0
	"""
	def determine_placement(self, user_id, tournament_id):
		player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			user_id = user_id,
			tournament_id = tournament_id
		)
		tournament = Tournament.objects.get_by_id(tournament_id)

		# Verify the tournament is completed
		if tournament.completed_at == None:
			raise ValidationError("Cannot determine placement until tourment is completed.")

		# -- Determine placement --
		placement = None
		# First, figure out if this player came first. They came first if:
		# (1) They did not get eliminated at all
		# (2) OR the number of rebuys exceeds the number of times they were eliminated.
		player_eliminations = TournamentElimination.objects.get_eliminations_by_tournament(tournament_id).filter(
			eliminatee_id = player.user.id
		)
		if len(player_eliminations) == 0:
			# They were never eliminated
			placement = 0
		if len(player_eliminations) < player.num_rebuys + 1:
			# The Tournament completed and they still had a rebuy remaining
			placement = 0
		if placement == None:
			# If they didn't come first, figure out what they placed.
			# This queryset is ordered from (last elim) -> (first elim)
			all_eliminations = TournamentElimination.objects.get_eliminations_by_tournament(tournament_id)
			# {user_id, timestamp of elimination}
			elimations_dict = {} 
			for elimination in all_eliminations:
				if elimination.eliminatee.id not in elimations_dict.keys():
					elimations_dict[elimination.eliminatee.id] = elimination.eliminated_at
				elif elimination.eliminated_at > elimations_dict[elimination.eliminatee.id]:
					# Only replace the value in the dictionary if the timestamp is newer (more recent)
					elimations_dict[elimination.eliminatee.id] = elimination.eliminated_at
			# Loop through the sorted list. Whatever index this user is in, thats what they placed
			# sorted_reversed_list = sorted(elimations_dict, key=elimations_dict.get).reverse()
			sorted_reversed_list = [k for k, v in sorted(elimations_dict.items(), key=lambda p: p[1], reverse=True)]
			for i,user_id in enumerate(sorted_reversed_list):
				if user_id == player.user.id:
					placement = i + 1 # add 1 b/c person in first won't show up in eliminations lists
					break
		return placement

	"""
	Determine the amount this player made from where they placed in the Tournament.
	This does not include bounties. This is strictly earnings from how they placed.
	"""
	def determine_placement_earnings(self, tournament, placement):
		placement_earnings = 0
		tournament_id = tournament.id
		players = TournamentPlayer.objects.get_tournament_players(tournament_id)
		num_rebuys = 0
		if tournament.tournament_structure.allow_rebuys:
			for player in players:
				num_rebuys += player.num_rebuys
		total_tournament_value = Tournament.objects.calculate_tournament_value(
			tournament_id = tournament_id, 
			num_rebuys = num_rebuys
		)
		bounty_amount = tournament.tournament_structure.bounty_amount
		if bounty_amount != None:
			# subtract the bounties from total value
			total_tournament_value -= Decimal(len(players) * bounty_amount)
			total_tournament_value -= Decimal(num_rebuys * bounty_amount)
		# Determine the % paid to this users placement
		for i,pct in enumerate(tournament.tournament_structure.payout_percentages):
			if i == placement:
				placement_earnings = Decimal(float(pct) / float(100.00) * float(total_tournament_value))
		return round(placement_earnings, 2)

	def create_tournament_player_result(self, user_id, tournament_id):
		player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			user_id = user_id,
			tournament_id = tournament_id
		)
		# Make sure a result doesn't already exist.
		results = TournamentPlayerResult.objects.get_results_for_user_by_tournament(
			user_id = user_id,
			tournament_id = tournament_id
		)
		# If any exist, delete them.
		for result in results:
			result.delete()

		tournament = Tournament.objects.get_by_id(tournament_id)

		# -- Get eliminations --
		eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
			tournament_id = tournament_id,
			eliminator_id = player.user.id
		)

		# -- Get bounty earnings (if this is a bounty tournament). Otherwise 0.00. --
		bounty_earnings = None
		if tournament.tournament_structure.bounty_amount != None:
			bounty_earnings = len(eliminations) * tournament.tournament_structure.bounty_amount
		else:
			bounty_earnings = round(Decimal(0.00), 2)

		# -- Get rebuys --
		rebuys = player.num_rebuys

		# -- Calculate 'investment' --
		buyin_amount = tournament.tournament_structure.buyin_amount
		investment = buyin_amount + (rebuys * buyin_amount)

		# -- Calculate placement --
		placement = self.determine_placement(user_id=player.user.id, tournament_id=tournament_id)

		# -- Calculate placement earnings --
		placement_earnings = self.determine_placement_earnings(
			tournament = tournament,
			placement = placement
		)

		# -- Calculate 'gross_earnings' --
		# Sum of placement_earnings + bounty_earnings
		gross_earnings = placement_earnings + bounty_earnings

		# -- Calculate 'net_earnings' --
		# Difference of gross_earnings - investment
		investment = buyin_amount + (rebuys * buyin_amount)
		net_earnings = gross_earnings - investment

		result = self.model(
			player = player,
			tournament = tournament,
			investment = investment,
			placement = placement,
			placement_earnings = placement_earnings,
			bounty_earnings = bounty_earnings,
			rebuys = rebuys,
			gross_earnings = gross_earnings,
			net_earnings = net_earnings
		)
		result.save(using=self._db)
		result.eliminations.add(*eliminations)
		result.save()
		return result

class TournamentPlayerResult(models.Model):
	player 				 		= models.ForeignKey(TournamentPlayer, on_delete=models.CASCADE)
	tournament 					= models.ForeignKey(Tournament, on_delete=models.CASCADE)

	# Total amount invested into this tournament. Initial buyin + rebuys
	investment 					= models.DecimalField(max_digits=9, decimal_places=2, blank=False, null=False)

	# Placement in the tournament (1st, 2nd, etc)
	placement 					= models.IntegerField()

	# Earnings strictle from placement
	placement_earnings 			= models.DecimalField(max_digits=9, decimal_places=2, blank=False, null=False)

	# Players who were eliminated by this user.
	eliminations 				= models.ManyToManyField(TournamentElimination)

	# Earnings from eliminations (Defaults to 0.00 if not a bounty tournament)
	bounty_earnings 			= models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)

	# Number of times rebought
	rebuys 						= models.IntegerField()

	# bounty_earnings + placement_earnings
	gross_earnings 				= models.DecimalField(max_digits=9, decimal_places=2, blank=False, null=False)

	# gross_earnings - investment
	net_earnings 				= models.DecimalField(max_digits=9, decimal_places=2, blank=False, null=False)

	objects = TournamentPlayerResultManager()

	def __str__(self):
		return f"TournamentPlayerResult data for {self.player.user.username}"

	def placement_string(self):
		return build_placement_string(self.placement)

	"""
	List of the user_ids of the users who were eliminated.
	"""
	def elimination_ids(self):
		return [f"{elimination.eliminatee.id}" for elimination in self.eliminations.all()]


# class TournamentGroup(models.Model):
# 	owner					= models.ForeignKey(User, on_delete=models.CASCADE)
# 	title 					= models.CharField(max_length=254, blank=False, null=False)
# 	tournaments



"""
TESTING...
from tournament.models import TournamentPlayer
from tournament.models import Tournament
from tournament.models import TournamentElimination
from tournament.models import TournamentStructure
from user.models import User
user=User.objects.get_by_email("mitch@tabian.ca")
user2=User.objects.get_by_email("pokerstats.db@gmail.com")
user3=User.objects.get_by_email("mitchtabian17@gmail.com")
tournament=Tournament.objects.get_by_id(1)
TournamentStructure.objects.create_tournament_struture_test("pokerstats tourny structure", "pokerstats.db@gmail.com", 80, 20, (80,10,10), True)
Tournament.objects.create_tournament_test("Pokerstats tourny", "pokerstats.db@gmail.com")
TournamentPlayer.objects.create_player_for_tournament(user.id, tournament.id)
TournamentElimination.objects.create_elimination(tournament.id,user.id, user2.id)
TournamentPlayer.objects.rebuy_by_user_id_and_tournament_id(user2.id, tournament.id)
"""




























