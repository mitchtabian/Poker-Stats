from decimal import Decimal
from django.db import models
import hashlib

from tournament.models import (
	Tournament,
	TournamentPlayerResult,
	TournamentElimination,
	TournamentSplitElimination,
	TournamentRebuy,
	TournamentPlayer
)
from user.models import User

class TournamentTotalsManager(models.Manager):

	"""
	from tournament_analytics.models import TournamentTotals
	TournamentTotals.objects.build_hash(1)
	"""
	def build_hash(self, tournaments):
		# Build a hash from the completed tournament ids.
		tournament_ids_string = ""
		for tournament in tournaments:
			tournament_ids_string += f"{tournament.id}+{tournament.completed_at}"
		hash_object = hashlib.sha1(tournament_ids_string.encode())
		hex_dig = hash_object.hexdigest()
		return hex_dig

	"""
	return True if TournamentTotals needs to be rebuilt for this user.

	return False if they do not need rebuilding.
	"""
	def do_tournament_totals_need_rebuild(self, user):
		players = TournamentPlayer.objects.get_all_tournament_players_by_user_id(user.id).exclude(tournament__completed_at=None)
		tournaments = [player.tournament for player in players]

		# They haven't participated in any tournaments. No need to build anything.
		if len(tournaments) == 0:
			return False

		# Get the TournamentTotals for this user.
		tournament_totals = self.get_tournament_totals_for_user(user).order_by("timestamp")

		# If they have existing TournamentTotals
		if len(tournament_totals) != 0:
			# Check to see if the hash has changed on the newest one.
			newest_totals = tournament_totals[len(tournament_totals) - 1]
			current_hash = newest_totals.rebuild_hash
			new_hash = self.build_hash(tournaments)
			# The hash is the same, do not rebuild the TournamentTotals.
			if current_hash == new_hash:
				return False
		# If the newest hash has changed, the tournaments this user has participated in have changed.
		return True

	"""
	Determine if a new TournamentTotals needs to be built for the given user.
	If it does not, return the existing ones.
	"""
	def get_or_build_tournament_totals_by_user_id(self, user_id):
		user = User.objects.get_by_id(user_id)

		# Get the existing TournamentTotals.
		tournament_totals = self.get_tournament_totals_for_user(user)

		if not self.do_tournament_totals_need_rebuild(user):
			return tournament_totals

		# If you get this far, TournamentTotals needs to be re-built.
		return self.generate_tournament_totals_retroactively_for_user(user=user)

	"""
	Build a new TournamentTotals object for the given user.

	This will build a single TournamentTotals object for all tournaments up to and including the 'tournament' passed as an argument.

	WARNING: This should only ever be invoked in two scenarios:
	1. You are completely resetting tournament totals for a user.
	2. A users tournament data has changed (there is a new hash), so the data needs to be regenerated.
	"""
	def build_tournament_totals_for_timestamp(self, user, participated_tournaments, end_at_tournament):
		tournaments = []
		for tournament in participated_tournaments:
			if tournament.completed_at <= end_at_tournament.completed_at:
				tournaments.append(tournament)

		new_hash = self.build_hash(tournaments)

		tournaments_played = len(tournaments)

		gross_earnings = Decimal(0.00)
		net_earnings = Decimal(0.00)
		losses = Decimal(0.00)
		eliminations_count = Decimal(0.00)
		rebuy_count = 0

		for tournament in tournaments:
			# This should return a queryset of length 1
			result = TournamentPlayerResult.objects.get_results_for_user_by_tournament(
				tournament_id = tournament.id,
				user_id = user.id
			)[0]
			gross_earnings += round(result.gross_earnings, 2)
			net_earnings += round(result.net_earnings, 2)
			losses += round(result.investment, 2)
			eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
				player_id = result.player.id
			)
			eliminations_count += len(eliminations)
			split_eliminations = TournamentSplitElimination.objects.get_split_eliminations_by_eliminator(
				player_id = result.player.id
			)
			for split_elimination in split_eliminations:
				eliminator_count = len(split_elimination.eliminators.all())
				eliminations_count += round(Decimal((1.00 / eliminator_count)), 2)
			rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = result.player
			)
			rebuy_count += len(rebuys)

		tournament_totals = self.model(
			user = user,
			rebuild_hash = new_hash,
			tournaments_played = tournaments_played,
			gross_earnings = gross_earnings,
			net_earnings = net_earnings,
			losses = losses,
			eliminations = eliminations_count,
			rebuys = rebuy_count,
			# override the timestamp since this is retroactive
			timestamp = end_at_tournament.completed_at
		)
		tournament_totals.save(using=self._db)
		return tournament_totals


	def get_tournament_totals_for_user(self, user):
		tournament_totals = super().get_queryset().filter(user=user)
		return tournament_totals

	"""
	Generate TournamentTotals data retroactively for a user.

	This is a very heavy operation. It's essentially a "reset" for all TournamentTotals data for a given user.
	"""
	def generate_tournament_totals_retroactively_for_user(self, user):
		# Delete existing totals.
		existing_tournament_totals = TournamentTotals.objects.get_tournament_totals_for_user(user)
		for total in existing_tournament_totals:
			total.delete()

		players = TournamentPlayer.objects.get_all_tournament_players_by_user_id(user.id).exclude(tournament__completed_at=None)
		participated_tournaments = [player.tournament for player in players]
		participated_tournaments = sorted(participated_tournaments, key=lambda x: x.completed_at, reverse=False)

		tournament_totals = []
		for tournament in participated_tournaments:
			# Generate new totals retroactively.
			tournament_total = self.build_tournament_totals_for_timestamp(
				user = user,
				participated_tournaments = participated_tournaments,
				end_at_tournament = tournament
			)
			tournament_totals.append(tournament_total)
		return tournament_totals
	

"""
Summary of all the tournaments a particular user has played in.

TODO talk about hash
"""
class TournamentTotals(models.Model):
	user					= models.ForeignKey(User, on_delete=models.CASCADE)
	rebuild_hash			= models.CharField(blank=False, null=False, max_length=255)
	tournaments_played		= models.IntegerField(blank=True, null=True, default=0)
	gross_earnings			= models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, default=Decimal(0.00))
	net_earnings			= models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, default=Decimal(0.00))
	losses					= models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, default=Decimal(0.00))
	eliminations			= models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True, default=Decimal(0.00))
	rebuys					= models.IntegerField(blank=True, null=True, default=0)
	timestamp				= models.DateTimeField(auto_now_add=False, null=False, blank=False)

	objects = TournamentTotalsManager()

	def __str__(self):
		return f"""\n
		User: {self.user.username}\n
		rebuild_hash: {self.rebuild_hash}\n
		tournaments_played: {self.tournaments_played}\n
		gross_earnings: {self.gross_earnings}\n
		net_earnings: {self.net_earnings}\n
		losses: {self.losses}\n
		eliminations: {self.eliminations}\n
		rebuys: {self.rebuys}\n
		"""














