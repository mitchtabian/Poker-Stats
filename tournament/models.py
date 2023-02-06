from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from user.models import User

PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(100)]


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

def validate_tournament_structure_owner(user, tournament_structure):
	if tournament_structure.user != user:
		raise ValidationError("You cannot use a Tournament Structure that you don't own.")

class TournamentManager(models.Manager):

	# Used for testing only. Selects the first TournamentStruture and builds a tournament.
	# from tournament.models import Tournament
	# Tournament.objects.create_tournament_test("tourny title", "mitch@tabian.ca")
	def create_tournament_test(self, title, admin_email):
		user = User.objects.get_by_email(admin_email)
		structures = TournamentStructure.objects.get_structures_by_user_email(admin_email)
		tournament = self.model(
			title=title,
			admin=user,
			tournament_structure=structures[0]
		)
		tournament.save(using=self._db)
		return tournament

	def create_tournament(self, title, user, tournament_structure):
		validate_tournament_structure_owner(user, tournament_structure)
		tournament = self.model(
			title=title,
			admin=user,
			tournament_structure=tournament_structure
		)
		tournament.save(using=self._db)
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
		tournament.completed_at = timezone.now()
		tournament.save(using=self._db)
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

class TournamentPlayerManager(models.Manager):

	# from tournament.models import TournamentPlayer
	# TournamentPlayer.objects.create_player_for_tournament(user.id, tourament.id)
	def create_player_for_tournament(self, user_id, tournament_id):
		user = User.objects.get_by_id(user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)
		player = self.get_tournament_player_by_user_id(user_id, tournament_id)

		# This player is already added to this tournament
		if player != None:
			raise ValidationError(f"{user.username} is already added to this tournament.")

		# This player has not been added to the tournament - add them.
		player = self.model(
			user=user,
			tournament=tournament
		)
		player.save(using=self._db)
		return player

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
		players = super().get_queryset().filter(tournament=tournament)
		return players

	"""
	A player has re-bought.
	Increment num_rebuys.

	Make sure not to increment num_rebuys if they're not out of rebuys.
	"""
	def rebuy_by_user_id_and_tournament_id(self, user_id, tournament_id):
		user = User.objects.get_by_id(user_id)
		tournament = Tournament.objects.get_by_id(tournament_id)
		tournament_player = TournamentPlayer.objects.get_tournament_player_by_user_id(user_id, tournament_id)

		# Verify the tournament allows rebuys
		if not tournament.tournament_structure.allow_rebuys:
			raise ValidationError(f"This tournament does not allow rebuys. Update the Tournament Structure.")

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
		
		# Make sure a player isn't trying to eliminate themselves.
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


		# Verify a multiple-eliminations aren't happening unless they've rebought.
		# Compare the numbers of times they've been eliminated against the number of rebuys.
		# Remember: If they've rebought once they will have one existing elimination.
		existing_eliminations = self.get_eliminations_by_tournament(tournament_id)
		player_eliminations = 0
		tournament_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			user_id=eliminatee.id,
			tournament_id=tournament_id,
		)
		for elimination in existing_eliminations:
			if elimination.eliminatee == eliminatee:
				player_eliminations += 1
			if player_eliminations > 0:
				if player_eliminations > tournament_player.num_rebuys:
					raise ValidationError(f"{eliminatee.username} has already been eliminated and has no more re-buys.")

		elimination = self.model(
			tournament=tournament,
			eliminator=eliminator,
			eliminatee=eliminatee
		)
		elimination.save(using=self._db)
		return elimination

"""
Tracks the data for eliminations. 

eliminator: Person who did the eliminating.

eliminatee: Person who got eliminated.
"""
class TournamentElimination(models.Model):
	tournament				= models.ForeignKey(Tournament, on_delete=models.CASCADE)
	eliminator				= models.ForeignKey(User, related_name="Eliminator", on_delete=models.CASCADE)	
	eliminatee				= models.ForeignKey(User, related_name="Eliminatee", on_delete=models.CASCADE)
	
	objects = TournamentEliminationManager()

	def __str__(self):
		return f"{self.eliminator.username} eliminated {self.eliminatee.username}."



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




























