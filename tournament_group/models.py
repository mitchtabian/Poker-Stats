from itertools import chain
from django.core.exceptions import ValidationError
from django.db import models


from tournament.models import (
	Tournament,
	TournamentPlayer
)
from user.models import User

class TournamentGroupManager(models.Manager):

	def create_tournament_group(self, admin, title):
		group = self.model(
			admin = admin,
			title = title
		)
		group.save(using=self._db)
		group.users.add(*[admin])
		group.save()
		return group

	def add_users_to_group(self, admin, group, users):
		if group.admin != admin:
			raise ValidationError("You're not the admin of that TournamentGroup.")

		user_set = set(users)
		if len(user_set) != len(users):
			raise ValidationError("There is a duplicate in the list of users you're trying to add to this TournamentGroup.")

		current_users = group.get_users()
		if len(user_set) != len(current_users):
			for user in users:
				if user in current_users:
					raise ValidationError(f"{user.username} is already in this TournamentGroup.")
		
		updated_group = group
		updated_group.users.add(*users)
		updated_group.save()
		return updated_group

	def remove_user_from_group(self, admin, group, user):
		if group.admin != admin:
			raise ValidationError(f"You're not the admin of that TournamentGroup.")

		current_users = group.get_users()
		if not user in current_users:
			raise ValidationError(f"{user.username} is not in this TournamentGroup.")

		# Find any tournaments that only this user participated in and remove them.
		unique_tournaments = self.find_tournaments_that_only_this_user_has_played(group = group, user = user)
		if len(unique_tournaments) > 0:
			for tournament in unique_tournaments:
				self.remove_tournament_from_group(admin = group.admin, group = group, tournament = tournament)

		updated_group = group
		updated_group.users.remove(*[user])
		updated_group.save()
		return updated_group

	def find_tournaments_that_only_this_user_has_played(self, group, user):
		tournaments = group.get_tournaments()

		current_users = group.get_users()
		if not user in current_users:
			raise ValidationError(f"{user.username} is not in this TournamentGroup.")

		# Find tournaments where 'user' is the only one who played.
		unique_tournaments = []
		for tournament in tournaments:
			players = TournamentPlayer.objects.get_tournament_players(
				tournament_id = tournament.id
			)
			player_users = [player.user for player in players]
			user_dict = {
				'count': 0
			}
			for a_user in player_users:
				if a_user in current_users:
					user_dict['count'] = user_dict['count'] + 1
					user_dict[a_user.id] = True
				if user_dict['count'] > 1:
					break
			if user_dict['count'] == 1 and user.id in user_dict:
				unique_tournaments.append(tournament)
			if user_dict['count'] == 0:
				# The TournamentGroup is corrupt. Somehow a Tournament was added that no players were a part of. Remove it.
				self.remove_tournament_from_group(admin = group.admin, group = group, tournament = tournament)
				
		return unique_tournaments

		if not self.has_at_least_one_user_played_in_tournament(group = group, tournament=tournament):
			raise ValidationError(f"None of the users in this TournamentGroup have played in {tournament.title}.")

	def add_tournaments_to_group(self, admin, group, tournaments):
		if group.admin != admin:
			raise ValidationError("You're not the admin of that TournamentGroup.")

		tournament_set = set(tournaments)
		if len(tournament_set) != len(tournaments):
			raise ValidationError("There is a duplicate in the list of tournaments you're trying to add to this TournamentGroup.")

		current_tournaments = group.get_tournaments()
		for tournament in tournaments:
			if tournament in current_tournaments:
				raise ValidationError(f"{tournament.title} is already in this TournamentGroup.")

		for tournament in tournaments:
			if not self.has_at_least_one_user_played_in_tournament(group = group, tournament=tournament):
				raise ValidationError(f"None of the users in this TournamentGroup have played in {tournament.title}.")

		updated_group = group
		updated_group.tournaments.add(*tournaments)
		updated_group.save()
		return updated_group

	def remove_tournament_from_group(self, admin, group, tournament):
		if group.admin != admin:
			raise ValidationError("You're not the admin of that TournamentGroup.")

		current_tournaments = group.get_tournaments()
		if not tournament in current_tournaments:
			raise ValidationError(f"{tournament.title} is not in this TournamentGroup.")

		updated_group = group
		updated_group.tournaments.remove(*[tournament])
		updated_group.save()
		return updated_group


	def update_tournament_group_title(self, admin, group, title):
		if group.admin != admin:
			raise ValidationError(f"You're not the admin of that TournamentGroup.")

		if title == None:
			raise ValidationError("Tournament Group title cannot be empty.")

		updated_group = group
		updated_group.title = title
		updated_group.save()
		return updated_group


	"""
	Determine if at least one of the users in the TournamentGroup have played in the given tournament.
	"""
	def has_at_least_one_user_played_in_tournament(self, group, tournament):
		users = group.get_users()
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		player_users = [player.user for player in players]
		is_at_least_one_user_in_tournament = False
		for user in player_users:
			if user in users:
				is_at_least_one_user_in_tournament = True
				break
		return is_at_least_one_user_in_tournament

	def get_by_id(self, id):
		try:
			tournament_group = self.get(id = id)
			return tournament_group
		except TournamentGroup.DoesNotExist:
			return None

	"""
	Get TournamentGroup's that this user is part of.
	"""
	def get_tournament_groups(self, user_id):
		user = User.objects.get_by_id(user_id)
		groups = super().get_queryset().filter(users__in=[user])
		return groups

	def get_by_id(self, id):
		try:
			tournament_group = self.get(id = id)
			return tournament_group
		except TournamentGroup.DoesNotExist:
			return None


class TournamentGroup(models.Model):
	admin					= models.ForeignKey(User, on_delete=models.CASCADE)
	title					= models.CharField(blank=False, null=False, max_length=255, unique=False)
	tournaments				= models.ManyToManyField(Tournament, related_name="tournaments_in_group")
	users					= models.ManyToManyField(User, related_name="users_in_group")

	objects = TournamentGroupManager()

	def __str__(self):
		return f"""\n
		Admin: {self.admin.username}\n
		Title: {self.title}\n
		Tournaments: {self.get_tournaments()}\n
		Users: {self.get_users()}\n
		"""

	def get_tournaments(self):
		return self.tournaments.all()

	def get_users(self):
		return self.users.all()
















