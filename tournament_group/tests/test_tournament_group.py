from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

from tournament.models import (
	Tournament
)
from tournament.test_util import (
	build_tournament,
	build_structure,
	add_players_to_tournament
)

from tournament_group.models import TournamentGroup

from user.models import User
from user.test_util import (
	create_users,
	build_user
)

class TournamentGroupTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True

	def setUp(self):
		# Build some users for the tests
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)

	def create_tournament_group(self, title, admin):
		group = TournamentGroup.objects.create_tournament_group(
			admin = admin,
			title = title
		)
		return group

	"""
	Create a new TournamentGroup and confirm the admin is added as a User.
	"""
	def test_create_tournament_group_admin_is_added_as_user(self):
		cat = User.objects.get_by_username("cat")
		title = "Cat's tournament group"
		group = self.create_tournament_group(
			admin = cat,
			title = title
		)

		groups = TournamentGroup.objects.get_tournament_groups(user_id = cat.id)

		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0].title, title)
		self.assertEqual(groups[0].admin, cat)
		self.assertEqual(len(groups[0].get_users()), 1)
		self.assertEqual(groups[0].get_users()[0], cat)

	"""
	Add a user to a TournamentGroup and validate all the logic in add_users_to_group.
	"""
	def test_add_users_to_group(self):
		cat = User.objects.get_by_username("cat")
		title = "Cat's tournament group"
		group = self.create_tournament_group(
			admin = cat,
			title = title
		)

		# Verify you cannot add users to a group if you are not admin
		dog = User.objects.get_by_username("dog")
		with self.assertRaisesMessage(ValidationError, "You're not the admin of that TournamentGroup."):
			TournamentGroup.objects.add_users_to_group(
				admin = dog,
				group = group,
				users = User.objects.all().exclude(username="cat")
			)

		# Verify you can't add the same user more than once.
		dog = User.objects.get_by_username("dog")
		with self.assertRaisesMessage(ValidationError, "There is a duplicate in the list of users you're trying to add to this TournamentGroup."):
			TournamentGroup.objects.add_users_to_group(
				admin = cat,
				group = group,
				users = [dog, dog]
			)

		# Add dog
		TournamentGroup.objects.add_users_to_group(
			admin = cat,
			group = group,
			users = [dog]
		)

		# Verify dog was added to the Group
		groups = TournamentGroup.objects.get_tournament_groups(user_id = cat.id)
		self.assertEqual(groups[0].get_users()[0], cat)
		self.assertEqual(groups[0].get_users()[1], dog)

		# Verify you can't add dog again.
		with self.assertRaisesMessage(ValidationError, f"{dog.username} is already in this TournamentGroup."):
			TournamentGroup.objects.add_users_to_group(
				admin = cat,
				group = group,
				users = [dog]
			)

	"""
	Remove a user to a TournamentGroup and validate all the logic in remove_user_from_group.
	"""
	def test_remove_user_from_group(self):
		cat = User.objects.get_by_username("cat")
		title = "Cat's tournament group"
		cats_group = self.create_tournament_group(
			admin = cat,
			title = title
		)
		# Add cats tournament to the group
		structure = build_structure(
			admin = cat, # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)

		tournament = build_tournament(structure, admin_user=cat)

		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = cat,
						tournament_id = tournament.id
					)

		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)

		# Add dog
		dog = User.objects.get_by_username("dog")
		TournamentGroup.objects.add_users_to_group(
			admin = cat,
			group = cats_group,
			users = [dog]
		)

		# Verify dog was added to the Group
		groups = TournamentGroup.objects.get_tournament_groups(user_id = cat.id)
		self.assertEqual(groups[0].get_users()[0], cat)
		self.assertEqual(groups[0].get_users()[1], dog)

		# Verify you cannot remove users from a group if you are not admin
		with self.assertRaisesMessage(ValidationError, "You're not the admin of that TournamentGroup."):
			TournamentGroup.objects.remove_user_from_group(
				admin = dog,
				group = cats_group,
				user = cat
			)

		# Verify you cannot remove a user who is not in the group.
		bird = User.objects.get_by_username("bird")
		with self.assertRaisesMessage(ValidationError, f"{bird.username} is not in this TournamentGroup."):
			TournamentGroup.objects.remove_user_from_group(
				admin = cat,
				group = cats_group,
				user = bird
			)

		# Add a tournament to the group that only dog participated in
		structure = build_structure(
			admin = dog, # Dog is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)
		tournament = build_tournament(structure = structure, admin_user = dog)

		Tournament.objects.start_tournament(user = dog, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = dog,
						tournament_id = tournament.id
					)

		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)

		# Verify there are two tournaments in the group
		groups = TournamentGroup.objects.get_tournament_groups(user_id = cat.id)
		self.assertEqual(len(groups[0].get_tournaments()), 2)
		self.assertEqual(groups[0].get_tournaments()[1].admin, cat)
		self.assertEqual(groups[0].get_tournaments()[0].admin, dog)

		# Now remove dog from the group. This should also remove dogs tournament since cat did not play in it.
		TournamentGroup.objects.remove_user_from_group(
				admin = cat,
				group = groups[0],
				user = dog
			)
		groups = TournamentGroup.objects.get_tournament_groups(user_id = cat.id)
		self.assertEqual(len(groups[0].get_tournaments()), 1)
		self.assertEqual(groups[0].get_tournaments()[0].admin, cat)

	"""
	Validate the logic in find_tournaments_that_only_specific_user_has_played.
	"""
	def test_find_tournaments_that_only_specific_user_has_played(self):
		cat = User.objects.get_by_username("cat")
		title = "Cat's tournament group"
		cats_group = self.create_tournament_group(
			admin = cat,
			title = title
		)
		# Add cats tournament to the group
		structure = build_structure(
			admin = cat, # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)

		tournament = build_tournament(structure, admin_user=cat)

		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = cat,
						tournament_id = tournament.id
					)

		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)

		# Add dog
		dog = User.objects.get_by_username("dog")
		TournamentGroup.objects.add_users_to_group(
			admin = cat,
			group = cats_group,
			users = [dog]
		)

		# Add a tournament to the group that only dog participated in
		structure = build_structure(
			admin = dog, # Dog is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)
		tournament = build_tournament(structure = structure, admin_user = dog)

		Tournament.objects.start_tournament(user = dog, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = dog,
						tournament_id = tournament.id
					)

		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)

		# Add bird
		bird = User.objects.get_by_username("bird")
		TournamentGroup.objects.add_users_to_group(
			admin = cat,
			group = cats_group,
			users = [bird]
		)

		# Add a tournament to the group that only bird participated in
		structure = build_structure(
			admin = bird, # bird is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)
		tournament = build_tournament(structure = structure, admin_user = bird)

		Tournament.objects.start_tournament(user = bird, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = bird,
						tournament_id = tournament.id
					)

		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)

		# Verify there are three tournaments in the group
		groups = TournamentGroup.objects.get_tournament_groups(user_id = cat.id)
		self.assertEqual(len(groups[0].get_tournaments()), 3)
		self.assertEqual(groups[0].get_tournaments()[2].admin, cat)
		self.assertEqual(groups[0].get_tournaments()[1].admin, dog)
		self.assertEqual(groups[0].get_tournaments()[0].admin, bird)

		# Find the tournaments in the group that only cat participated in.
		cats_groups = TournamentGroup.objects.get_tournament_groups(
			user_id = cat.id
		)
		tournaments = TournamentGroup.objects.find_tournaments_that_only_this_user_has_played(
			group = cats_groups[0],
			user = cat
		)
		self.assertEqual(len(tournaments), 1)
		self.assertEqual(tournaments[0].admin, cat)

		# Find the tournaments in the group that only dog participated in.
		tournaments = TournamentGroup.objects.find_tournaments_that_only_this_user_has_played(
			group = cats_groups[0],
			user = dog
		)
		self.assertEqual(len(tournaments), 1)
		self.assertEqual(tournaments[0].admin, dog)

		# Find the tournaments in the group that only bird participated in.
		tournaments = TournamentGroup.objects.find_tournaments_that_only_this_user_has_played(
			group = cats_groups[0],
			user = bird
		)
		self.assertEqual(len(tournaments), 1)
		self.assertEqual(tournaments[0].admin, bird)


	"""
	Test the logic in test_add_tournaments_to_group.
	"""
	def test_add_tournaments_to_group(self):
		cat = User.objects.get_by_username("cat")
		title = "Cat's tournament group"
		cats_group = self.create_tournament_group(
			admin = cat,
			title = title
		)
		# Add cats tournament to the group
		structure = build_structure(
			admin = cat, # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)

		dog = User.objects.get_by_username("dog")
		tournament = build_tournament(structure, admin_user=cat)

		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = cat,
						tournament_id = tournament.id
					)

		# Verify you cannot add tournaments to a group if you are not admin
		with self.assertRaisesMessage(ValidationError, "You're not the admin of that TournamentGroup."):
			TournamentGroup.objects.add_tournaments_to_group(
				admin = dog,
				group = cats_group,
				tournaments = [tournament]
			)

		# Verify you cannot add the same tournament more than once.
		with self.assertRaisesMessage(ValidationError, "There is a duplicate in the list of tournaments you're trying to add to this TournamentGroup."):
			TournamentGroup.objects.add_tournaments_to_group(
				admin = cat,
				group = cats_group,
				tournaments = [tournament, tournament]
			)

		# Add a tournament to the group
		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)
		groups = TournamentGroup.objects.get_tournament_groups(user_id=cat.id)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0].admin, cat)
		self.assertEqual(len(groups[0].get_tournaments()), 1)
		self.assertEqual(groups[0].get_tournaments()[0].admin, cat)

		# Verify you cannot add the same tournament again.
		with self.assertRaisesMessage(ValidationError, f"{tournament.title} is already in this TournamentGroup."):
			TournamentGroup.objects.add_tournaments_to_group(
				admin = cat,
				group = cats_group,
				tournaments = [tournament]
			)

		# Verify you cannot add a Tournament to the Group that none of the users in the group have played in.
		structure = build_structure(
			admin = dog, # Dog is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)
		tournament = build_tournament(structure = structure, admin_user = dog)
		with self.assertRaisesMessage(ValidationError, f"None of the users in this TournamentGroup have played in {tournament.title}."):
			TournamentGroup.objects.add_tournaments_to_group(
				admin = cat,
				group = cats_group,
				tournaments = [tournament]
			)

	
	"""
	Test the logic in remove_tournament_from_group.
	"""
	def test_remove_tournament_from_group(self):
		cat = User.objects.get_by_username("cat")
		title = "Cat's tournament group"
		cats_group = self.create_tournament_group(
			admin = cat,
			title = title
		)
		# Add cats tournament to the group
		structure = build_structure(
			admin = cat, # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)

		dog = User.objects.get_by_username("dog")
		tournament = build_tournament(structure, admin_user=cat)

		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		tournament = Tournament.objects.complete_tournament(
						user = cat,
						tournament_id = tournament.id
					)

		# Add a tournament to the group
		TournamentGroup.objects.add_tournaments_to_group(
			admin = cat,
			group = cats_group,
			tournaments = [tournament]
		)
		groups = TournamentGroup.objects.get_tournament_groups(user_id=cat.id)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0].admin, cat)
		self.assertEqual(len(groups[0].get_tournaments()), 1)
		self.assertEqual(groups[0].get_tournaments()[0].admin, cat)

		# Verify you cannot remove a tournament if you are not the admin
		with self.assertRaisesMessage(ValidationError, "You're not the admin of that TournamentGroup."):
			TournamentGroup.objects.remove_tournament_from_group(
				admin = dog,
				group = cats_group,
				tournament = tournament
			)

		# Verify you cannot remove a tournament that is not in the group
		structure = build_structure(
			admin = dog, # Dog is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = True
		)
		dog_tournament = build_tournament(structure = structure, admin_user = dog)

		Tournament.objects.start_tournament(user = dog, tournament_id = dog_tournament.id)
		dog_tournament = Tournament.objects.complete_tournament(
						user = dog,
						tournament_id = dog_tournament.id
					)

		with self.assertRaisesMessage(ValidationError, f"{dog_tournament.title} is not in this TournamentGroup."):
			TournamentGroup.objects.remove_tournament_from_group(
				admin = cat,
				group = cats_group,
				tournament = dog_tournament
			)

		# Remove the Tournament from the group
		TournamentGroup.objects.remove_tournament_from_group(
			admin = cat,
			group = cats_group,
			tournament = tournament
		)
		groups = TournamentGroup.objects.get_tournament_groups(user_id=cat.id)
		self.assertEqual(len(groups), 1)
		self.assertEqual(len(groups[0].get_tournaments()), 0)

		

























