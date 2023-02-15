from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

from tournament.models import (
	TournamentInvite,
	TournamentPlayerResult,
	TournamentStructure,
	TournamentElimination,
	Tournament,
	TournamentPlayer,
	TournamentState,
	TournamentRebuy
)
from tournament.test_util import (
	add_players_to_tournament,
	build_tournament,
	build_structure,
	eliminate_players_and_complete_tournament,
	eliminate_all_players_except,
	eliminate_player,
	PlayerPlacementData,
	rebuy_for_test
)
from tournament.util import PlayerTournamentPlacement, build_placement_string
from user.models import User
from user.test_util import (
	create_users,
	build_user
)

class TournamentInvitesTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True

	def setUp(self):
		# Build some users for the tests
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)

		# Build a Structure with no bounties and no rebuys
		structure = build_structure(
			admin = users[0], # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = False
		)

		tournament = build_tournament(structure)

	"""
	Verify correct invitation sent
	"""
	def test_user_is_invited_to_tournament(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Invite a player
		TournamentInvite.objects.send_invite(
			sent_from_user_id = admin.id,
			send_to_user_id = users[1].id,
			tournament_id = tournament.id
		)

		# Verify the correct player got an invitation
		invites = TournamentInvite.objects.find_pending_invites(
			send_to_user_id = users[1].id,
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 1)
		self.assertEqual(invites[0].send_to, users[1])

		# Verify a TournamentPlayer is created
		player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = users[1].id
		)
		self.assertEqual(player.user.id, users[1].id)

		# Verify has_joined_tournament is False because they haven't accepted the invite.
		has_joined_tournament = TournamentPlayer.objects.has_player_joined_tournament(
			tournament_id = tournament.id,
			player_id = player.id
		)
		self.assertEqual(has_joined_tournament, False)

	"""
	Verify cannot send duplicate invites
	"""
	def test_cannot_send_duplicate_invites(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Invite a player
		TournamentInvite.objects.send_invite(
			sent_from_user_id = admin.id,
			send_to_user_id = users[1].id,
			tournament_id = tournament.id
		)
		# Try to invite again and verify it fails
		with self.assertRaisesMessage(ValidationError, f"{users[1].username} has already been invited."):
			TournamentInvite.objects.send_invite(
				sent_from_user_id = admin.id,
				send_to_user_id = users[1].id,
				tournament_id = tournament.id
			)

	"""
	Verify only the admin can send invites.
	"""
	def test_cannot_invite_unless_admin(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Try to send an invitation when not the admin
		new_user = create_users(['horse'])[0]
		for user in users:
			if user.username != "cat":
				with self.assertRaisesMessage(ValidationError, "You can't send invites unless you're the admin."):
					TournamentInvite.objects.send_invite(
						sent_from_user_id = user.id,
						send_to_user_id = new_user.id,
						tournament_id = tournament.id
					)

	"""
	Verify admin is not inviting themself. The admin is automatically added to a Tournament when its created.
	"""
	def test_admin_cannot_invite_themself(self):
		tournament = Tournament.objects.get_by_id(1)
		admin = User.objects.get_by_username("cat")

		# Try to send an invitation when not the admin
		with self.assertRaisesMessage(ValidationError, "You can't invite yourself to the Tournament."):
			TournamentInvite.objects.send_invite(
				sent_from_user_id = admin.id,
				send_to_user_id = admin.id,
				tournament_id = tournament.id
			)

	"""
	Verify can't invite to a completed tournament.
	"""
	def test_cannot_invite_to_completed_tournament(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Start the Tournament
		Tournament.objects.start_tournament(user = admin, tournament_id = tournament.id)
		# Complete Tournament
		eliminate_players_and_complete_tournament(admin = admin, tournament = tournament)

		# Try to send invites to completed tournament
		for user in users:
			if user.username != "cat":
				with self.assertRaisesMessage(ValidationError, "You can't invite to a Tournment that's completed."):
					TournamentInvite.objects.send_invite(
						sent_from_user_id = admin.id,
						send_to_user_id = user.id,
						tournament_id = tournament.id
					)

	"""
	Verify can't invite to a started tournament.
	"""
	def test_cannot_invite_to_started_tournament(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Start the Tournament
		Tournament.objects.start_tournament(user = admin, tournament_id = tournament.id)

		# Try to send invites to completed tournament
		for user in users:
			if user.username != "cat":
				with self.assertRaisesMessage(ValidationError, "You can't invite to a Tournment that's started."):
					TournamentInvite.objects.send_invite(
						sent_from_user_id = admin.id,
						send_to_user_id = user.id,
						tournament_id = tournament.id
					)

	"""
	Verify can't invite a player who is already in the Tournament
	"""
	def test_admin_cannot_invite_tournament_player(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Add the users to the Tournament as TournamentPlayer's
		add_players_to_tournament(
			# Remove the admin since they are already a player automatically
			users = [value for value in users if value.username != "cat"],
			tournament = tournament
		)

		# Get the players
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		# Try to invite the players
		for player in players:
			if player.user.username != "cat":
				with self.assertRaisesMessage(ValidationError, f"{player.user.username} is already in this tournament."):
					TournamentInvite.objects.send_invite(
						sent_from_user_id = admin.id,
						send_to_user_id = player.user.id,
						tournament_id = tournament.id
					)
			else:
				with self.assertRaisesMessage(ValidationError, "You can't invite yourself to the Tournament."):
					TournamentInvite.objects.send_invite(
						sent_from_user_id = admin.id,
						send_to_user_id = player.user.id,
						tournament_id = tournament.id
					)

	"""
	Verify can't uninvite unless admin
	"""
	def test_admin_cannot_uninvite_unless_admin(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Invite all users
		for user in users:
			if user.username != "cat":
				TournamentInvite.objects.send_invite(
					sent_from_user_id = admin.id,
					send_to_user_id = user.id,
					tournament_id = tournament.id
				)

		# Verify they all got invitations
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 8)
		
		# Try to uninvite players when not admin
		for invite in invites:
			if invite.tournament.admin.username != "cat":
				with self.assertRaisesMessage(ValidationError, "You can't remove invites unless you're the admin."):
					TournamentInvite.objects.send_invite(
						sent_from_user_id = invite.send_to.id,
						send_to_user_id = admin.id, # this doesn't matter in this case
						tournament_id = tournament.id
					)
		
	"""
	Verify can't uninvite someone who has never been invited
	"""
	def test_admin_cannot_uninvite_if_no_invite_exists(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# Invite all users except "dog"
		for user in users:
			if user.username != "cat" and user.username != "dog":
				TournamentInvite.objects.send_invite(
					sent_from_user_id = admin.id,
					send_to_user_id = user.id,
					tournament_id = tournament.id
				)

		# Verify cannot uninvite "Dog" since they were never invited.
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 7)
		dog = User.objects.get_by_username("dog")
		with self.assertRaisesMessage(ValidationError, "That player does not have an invition to this tournament."):
			TournamentInvite.objects.uninvite_player_from_tournament(
				admin_id = admin.id,
				uninvite_user_id = dog.id,
				tournament_id = tournament.id
			)

	"""
	Verify invites were sent and then removed
	"""
	def test_invites_sent_and_removed(self):
		tournament = Tournament.objects.get_by_id(1)
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")

		# send invitations
		for user in users:
			if user.username != "cat":
				TournamentInvite.objects.send_invite(
					sent_from_user_id = admin.id,
					send_to_user_id = user.id,
					tournament_id = tournament.id
				)

		# Verify all users were invited
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 8)

		# Uninvite everyone
		for invite in invites:
			TournamentInvite.objects.uninvite_player_from_tournament(
				admin_id = admin.id,
				uninvite_user_id = invite.send_to.id,
				tournament_id = tournament.id
			)
		# Verify all invitations were removed.
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 0)

		# Verify the TournamentPlayer's were deleted except the admin
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		self.assertEqual(len(players), 1)
		self.assertEqual(players[0].user, admin)


class TournamentPlayersTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True

	def setup_tournament(self, admin, allow_rebuys):
		# Build a Structure that allows rebuys
		structure = build_structure(
			admin = admin,
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = allow_rebuys
		)

		return build_tournament(structure)


	def setUp(self):
		# Build some users for the tests
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)

	"""
	Verify join_tournament
	"""
	def test_join_tournament(self):
		users = User.objects.all()
		admin = User.objects.get_by_username("cat")
		tournament = self.setup_tournament(
			admin = admin,
			allow_rebuys = False
		)

		# send invitations
		for user in users:
			if user.username != "cat":
				TournamentInvite.objects.send_invite(
					sent_from_user_id = admin.id,
					send_to_user_id = user.id,
					tournament_id = tournament.id
				)

		# Verify all users were invited
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 8)

		# join everyone except users[8]
		for invite in invites:
			if invite.send_to != users[8]:
				player = TournamentPlayer.objects.get_tournament_player_by_user_id(
					tournament_id = tournament.id,
					user_id = invite.send_to.id
				)
				TournamentPlayer.objects.join_tournament(
					player = player
				)

		# Verify all invitations were removed except users[8] invitation.
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(invites), 1)
		self.assertEqual(invites[0].send_to, users[8])

		# Verify the TournamentPlayer's have has_joined_tournament == True except users[8]
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		self.assertEqual(len(players), 9)
		for player in players:
			if player.user == users[8]:
				has_joined_tournament = TournamentPlayer.objects.has_player_joined_tournament(
					tournament_id = tournament.id,
					player_id = player.id
				)
				self.assertEqual(has_joined_tournament, False)
			else:
				has_joined_tournament = TournamentPlayer.objects.has_player_joined_tournament(
					tournament_id = tournament.id,
					player_id = player.id
				)
				self.assertEqual(has_joined_tournament, True)

	"""
	Verify the players are added correctly to the Tournament.
	"""
	def test_players_are_added_to_tournament(self):
		admin = User.objects.get_by_username("cat")

		tournament = self.setup_tournament(admin=admin, allow_rebuys=False)

		users = User.objects.all()

		# Add the users to the Tournament as TournamentPlayer's
		add_players_to_tournament(
			users = users,
			tournament = tournament
		)

		# Get the players
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		# Verify there are 9 players
		self.assertEqual(len(players), 9)

		# Verify there are no duplicate players
		usernames = map(lambda player: player.user.username, players)
		usernames_set = set(usernames)
		self.assertEqual(len(usernames_set), 9)

		# Verify you can't add a player twice
		for player in players:
			with self.assertRaisesMessage(ValidationError, f'{player.user.username} is already added to this tournament.'):
				TournamentPlayer.objects.create_player_for_tournament(
					user_id = player.user.id,
					tournament_id = tournament.id
				)

	"""
	Verify you can't add or remove players from a Tournament that is completed.
	"""
	def test_cannot_add_or_remove_players_from_completed_tournament(self):
		admin = User.objects.get_by_username("cat")

		tournament = self.setup_tournament(admin=admin, allow_rebuys=False)

		users = User.objects.all()

		# Add the users to the Tournament as TournamentPlayer's
		add_players_to_tournament(
			# Remove the admin since they are already a player automatically
			users = [value for value in users if value.username != "cat"],
			tournament = tournament
		)

		Tournament.objects.start_tournament(user = admin, tournament_id = tournament.id)
		eliminate_players_and_complete_tournament(admin = admin, tournament = tournament)

		# Verify cannot add
		new_user = create_users(['horse'])[0]
		with self.assertRaisesMessage(ValidationError, "You can't add players to a Tournment that is completed."):
			TournamentPlayer.objects.create_player_for_tournament(
				user_id = new_user.id,
				tournament_id = tournament.id
			)

		# Verify cannot remove
		with self.assertRaisesMessage(ValidationError, "You can't remove players from a Tournment that is completed"):
			TournamentPlayer.objects.remove_player_from_tournament(
				removed_by_user_id = users[0].id,
				removed_user_id = users[1].id,
				tournament_id = tournament.id
			)

	"""
	Verify you can't add or remove players from a Tournament that is started.
	"""
	def test_cannot_add_or_remove_players_from_started_tournament(self):
		admin = User.objects.get_by_username("cat")

		tournament = self.setup_tournament(admin=admin, allow_rebuys=False)

		users = User.objects.all()

		# Add the users to the Tournament as TournamentPlayer's
		add_players_to_tournament(
			# Remove the admin since they are already a player automatically
			users = [value for value in users if value.username != "cat"],
			tournament = tournament
		)

		Tournament.objects.start_tournament(user = admin, tournament_id = tournament.id)

		# Verify cannot add
		new_user = create_users(['horse'])[0]
		with self.assertRaisesMessage(ValidationError, "You can't add players to a Tournment that is started."):
			TournamentPlayer.objects.create_player_for_tournament(
				user_id = new_user.id,
				tournament_id = tournament.id
			)
		# Verify cannot remove
		with self.assertRaisesMessage(ValidationError, "You can't remove players from a Tournment that is started."):
			TournamentPlayer.objects.remove_player_from_tournament(
				removed_by_user_id = users[0].id,
				removed_user_id = users[1].id,
				tournament_id = tournament.id
			)

class TournamentRebuysTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True
	
	def setup_tournament(self, allow_rebuys):
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)
		structure = build_structure(
			admin = users[0], # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = allow_rebuys
		)

		tournament = build_tournament(structure)

		# Add the users to the Tournament as TournamentPlayer's
		add_players_to_tournament(
			# Remove the admin since they are already a player automatically
			users = [value for value in users if value.username != "cat"],
			tournament = tournament
		)

		return tournament

	"""
	rebuy: player is not part of tournament.
	"""
	def test_rebuy_player_is_not_part_of_tournament(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)
		new_user = create_users(['horse'])[0]
		with self.assertRaisesMessage(ValidationError, "That player is not part of this tournament."):
			TournamentRebuy.objects.rebuy(
				tournament_id = tournament.id,
				player_id = new_user.id
			)

	"""
	rebuy: cannot rebuy if tournament is not active
	"""
	def test_rebuy_cannot_rebuy_if_tournament_not_active(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)
		cat = User.objects.get_by_username("cat")

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		# Activate
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Go through the players and eliminate
		for player in players:
			if player != cat_player:
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)

		# Deactivate the tournament
		tournament.started_at = None
		tournament.save()

		# Go through the players and try to rebuy
		for player in players:
			if player != cat_player:
				with self.assertRaisesMessage(ValidationError, "Cannot rebuy if Tournament is not active."):
					TournamentRebuy.objects.rebuy(
						tournament_id = tournament.id,
						player_id = player.id
					)

	"""
	rebuy: Tournament does not allow rebuys
	"""
	def test_rebuy_tournament_does_not_allow_rebuys(self):
		tournament = self.setup_tournament(
			allow_rebuys = False
		)

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		for player in players:
			with self.assertRaisesMessage(ValidationError, "This tournament does not allow rebuys. Update the Tournament Structure."):
				TournamentRebuy.objects.rebuy(
					tournament_id = tournament.id,
					player_id = player.id
				)

	"""
	rebuy: Cannot rebuy if player has not been eliminated.
	"""
	def test_rebuy_cannot_rebuy_if_player_not_elimianted(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		cat = User.objects.get_by_username("cat")

		# Activate
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		for player in players:
			with self.assertRaisesMessage(ValidationError, f"{player.user.username} has not been eliminated. Eliminate them before adding another rebuy."):
				TournamentRebuy.objects.rebuy(
					tournament_id = tournament.id,
					player_id = player.id
				)

	"""
	rebuy: success.
	"""
	def test_rebuy_success(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		cat = User.objects.get_by_username("cat")

		# Activate
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Go through the players and eliminate, then rebuy
		for player in players:
			if player != cat_player:
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)
				rebuy = TournamentRebuy.objects.rebuy(
					tournament_id = tournament.id,
					player_id = player.id
				)
				self.assertEqual(rebuy.player.tournament, tournament)
				self.assertEqual(rebuy.player.user, player.user)
				self.assertEqual(rebuy.player, player)

	"""
	get_rebuys_for_user: success.
	"""
	def test_rebuys_for_user_success(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		cat = User.objects.get_by_username("cat")

		# Activate
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Go through the players and invoke get_rebuys_for_user. They should all be 0.
		for player in players:
			rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			self.assertEqual(len(rebuys), 0)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Eliminate players and rebuy on everyone except cat.
		for player in players:
			if player.user.username != "cat":
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)
				rebuy = TournamentRebuy.objects.rebuy(
					tournament_id = tournament.id,
					player_id = player.id
				)
				self.assertEqual(rebuy.player.tournament, tournament)
				self.assertEqual(rebuy.player, player)
				self.assertEqual(rebuy.player.user, player.user)

		# Go through the players and invoke get_rebuys_for_user. They should all be 1 except cat.
		for player in players:
			rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			if player == cat_player:
				self.assertEqual(len(rebuys), 0)
			else:
				self.assertEqual(len(rebuys), 1)


	"""
	get_rebuys_for_tournament: success.
	"""
	def test_rebuys_for_tournament_success(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		cat = User.objects.get_by_username("cat")

		# Activate
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Get total rebuys for tournament
		rebuys = TournamentRebuy.objects.get_rebuys_for_tournament(
			tournament_id = tournament.id,
		)
		self.assertEqual(len(rebuys), 0)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Eliminate players and rebuy on everyone except cat.
		for player in players:
			if player.user.username != "cat":
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)
				rebuy = TournamentRebuy.objects.rebuy(
					tournament_id = tournament.id,
					player_id = player.id
				)
				self.assertEqual(rebuy.player.tournament, tournament)
				self.assertEqual(rebuy.player, player)
				self.assertEqual(rebuy.player.user, player.user)

		# Get rebuys for tournament. Everyone rebought except cat, so rebuys should be 8.
		rebuys = TournamentRebuy.objects.get_rebuys_for_tournament(
			tournament_id = tournament.id,
		)
		self.assertEqual(len(rebuys), 8)

	"""
	delete_tournament_rebuys: success.
	"""
	def test_delete_tournament_rebuys(self):
		tournament = self.setup_tournament(
			allow_rebuys = True
		)

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		cat = User.objects.get_by_username("cat")

		# Activate
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Eliminate players and rebuy on everyone except cat.
		for player in players:
			if player != cat_player:
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)
				rebuy = TournamentRebuy.objects.rebuy(
					tournament_id = tournament.id,
					player_id = player.id
				)
				self.assertEqual(rebuy.player.tournament, tournament)
				self.assertEqual(rebuy.player.user, player.user)
				self.assertEqual(rebuy.player, player)

		# Get rebuys for tournament. Everyone rebought except cat, so rebuys should be 8.
		rebuys = TournamentRebuy.objects.get_rebuys_for_tournament(
			tournament_id = tournament.id,
		)
		self.assertEqual(len(rebuys), 8)

		# Delete the rebuys
		TournamentRebuy.objects.delete_tournament_rebuys(
			tournament_id = tournament.id
		)

		# Verify rebuy data is deleted
		rebuys = TournamentRebuy.objects.get_rebuys_for_tournament(
			tournament_id = tournament.id,
		)
		self.assertEqual(len(rebuys), 0)


class TournamentEliminationsTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True
	
	def setUp(self):
		# Build some users for the tests
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)

		# Build a Structure with no bounties and no rebuys
		structure = build_structure(
			admin = users[0], # Cat is admin
			buyin_amount = 115,
			bounty_amount = 15,
			payout_percentages = (60, 30, 10),
			allow_rebuys = False
		)

		tournament = build_tournament(structure)

		# Add the users to the Tournament as TournamentPlayer's
		add_players_to_tournament(
			# Remove the admin since they are already a player automatically
			users = [value for value in users if value.username != "cat"],
			tournament = tournament
		)

	"""
	Test the eliminations
	"""
	def test_eliminations(self):
		tournament = Tournament.objects.get_by_id(1)
		tournament_id = tournament.id
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		# Start
		Tournament.objects.start_tournament(user = tournament.admin, tournament_id = tournament.id)

		# -- Create eliminations --

		# player0 eliminates player1
		eliminate_player(
			tournament_id = tournament_id,
			eliminator_id = players[0].id,
			eliminatee_id = players[1].id
		)

		# player2 eliminates player3
		eliminate_player(
			tournament_id = tournament_id,
			eliminator_id = players[2].id,
			eliminatee_id = players[3].id
		)

		# player4 eliminates player5
		eliminate_player(
			tournament_id = tournament_id,
			eliminator_id = players[4].id,
			eliminatee_id = players[5].id
		)

		# player6 eliminates player7
		eliminate_player(
			tournament_id = tournament_id,
			eliminator_id = players[6].id,
			eliminatee_id = players[7].id
		)

		# player0 eliminates player8
		eliminate_player(
			tournament_id = tournament_id,
			eliminator_id = players[0].id,
			eliminatee_id = players[8].id
		)

		# At this point everyone is eliminated except player0

		# -- Verify eliminations --

		# Verify the eliminations by player0
		eliminations0 = TournamentElimination.objects.get_eliminations_by_eliminator(
			player_id = players[0].id
		)
		self.assertEqual(eliminations0[0].eliminatee.tournament, tournament)
		self.assertEqual(eliminations0[0].eliminator.tournament, tournament)
		self.assertEqual(eliminations0[1].eliminatee.tournament, tournament)
		self.assertEqual(eliminations0[1].eliminator.tournament, tournament)
		self.assertEqual(len(eliminations0), 2)
		# player0 eliminated player1
		self.assertEqual(eliminations0[0].eliminator, players[0])
		self.assertEqual(eliminations0[0].eliminatee, players[1])
		# player0 eliminated player8
		self.assertEqual(eliminations0[1].eliminator, players[0])
		self.assertEqual(eliminations0[1].eliminatee, players[8])

	"""
	Cannot eliminate a player who is not part of the tournament and cannot perform an elimination if the eliminator
	is not part of the tournment.
	"""
	def test_cannot_eliminate_user_who_has_not_joined_tournament(self):
		tournament = Tournament.objects.get_by_id(1)
		tournament_id = tournament.id
		new_user = create_users(['horse'])[0]

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		# Start
		Tournament.objects.start_tournament(user = tournament.admin, tournament_id = tournament.id)

		with self.assertRaisesMessage(ValidationError, "Eliminatee is not part of that Tournament."):
			eliminate_player(
				tournament_id = tournament_id,
				eliminator_id = players[0].user.id,
				eliminatee_id = new_user.id # This will fail b/c its not a TournamentPlayer
			)

		with self.assertRaisesMessage(ValidationError, "Eliminator is not part of that Tournament."):
			eliminate_player(
				tournament_id = tournament_id,
				eliminator_id = new_user.id, # This will fail b/c its not a TournamentPlayer
				eliminatee_id = players[0].user.id 
			)

	"""
	Verifying the is_player_eliminated function works as expected
	"""
	def test_is_eliminated(self):
		tournament = Tournament.objects.get_by_id(1)
		tournament_id = tournament.id

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("user__username")

		# Start
		Tournament.objects.start_tournament(user = tournament.admin, tournament_id = tournament.id)

		admin_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = tournament.admin.id
		)

		# eliminate player0
		eliminate_player(
			tournament_id = tournament.id,
			eliminator_id = admin_player.id,
			eliminatee_id = players[0].id
		)

		# Confirm only player0 is eliminated
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(tournament_id)
		for elimination in eliminations:
			is_eliminated = TournamentElimination.objects.is_player_eliminated(
				player_id=elimination.eliminatee.id,
			)
			if elimination.eliminatee.id == players[0].id:
				self.assertEqual(is_eliminated, True)
			else:
				self.assertEqual(is_eliminated, False)


	"""
	Verify you cannot eliminate a player that is already eliminated
	"""
	def test_cannot_eliminate_player_who_is_already_eliminated(self):
		tournament = Tournament.objects.get_by_id(1)
		tournament_id = tournament.id

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("user__username")

		# eliminate player0
		eliminate_player(
			tournament_id = tournament_id,
			eliminator_id = players[1].id,
			eliminatee_id = players[0].id
		)
		# Try to eliminate again. This will fail because they have already been eliminated and have no more rebuys.
		with self.assertRaisesMessage(ValidationError, f"{players[0].user.username} has already been eliminated and has no more re-buys."):
			eliminate_player(
				tournament_id = tournament_id,
				eliminator_id = players[1].id,
				eliminatee_id = players[0].id
			)

	"""
	Verify you cannot eliminate a player when the tournament is not started.
	"""
	def test_cannot_eliminate_player_who_is_already_eliminated(self):
		tournament = Tournament.objects.get_by_id(1)
		tournament_id = tournament.id

		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("user__username")

		with self.assertRaisesMessage(ValidationError, "You can only eliminate players if the Tournament is Active."):
			eliminate_player(
				tournament_id = tournament_id,
				eliminator_id = players[1].id,
				eliminatee_id = players[0].id
			)

	"""
	Test cannot eliminate the final player. The Tournament should be completed.
	"""
	def test_cannot_eliminate_last_player(self):
		tournament = Tournament.objects.get_by_id(1)
		tournament_id = tournament.id
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)

		# Start
		Tournament.objects.start_tournament(user = tournament.admin, tournament_id = tournament.id)

		# -- Create eliminations --

		# Eliminate all players except player0
		eliminate_all_players_except(
			players = players,
			except_player = players[0],
			tournament = tournament
		)

		# At this point everyone is eliminated except player0
		# Try to eliminate them.
		with self.assertRaisesMessage(ValidationError, "You can't eliminate any more players. Complete the Tournament."):
			eliminate_player(
				tournament_id = tournament_id,
				eliminator_id = players[8].id,
				eliminatee_id = players[0].id
			)


class TournamentTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True
	
	"""
	bounty_amount: If None, this is not a bounty tournament.
	"""
	def build_structure(self, user, buyin_amount, bounty_amount, payout_percentages, allow_rebuys):
		structure = build_structure(
			admin = user,
			buyin_amount = buyin_amount,
			bounty_amount = bounty_amount,
			payout_percentages = payout_percentages,
			allow_rebuys = allow_rebuys
		)
		return structure
	
	def build_tournament(self, admin, title, structure):
		tournament = Tournament.objects.create_tournament(
			title = title,
			user = admin,
			tournament_structure = structure
		)
		return tournament

	"""
	Verify any error occurs, the follow must happen:
		1. eliminations deleted
		2. rebuys deleted
		3. Tournament.started_at = None
		4. Tournament.completed_at = None
	"""
	def verify_tournament_reset(self, tournament_id):
		tournament = Tournament.objects.get_by_id(tournament_id)
		self.assertEqual(tournament.completed_at, None)
		self.assertEqual(tournament.started_at, None)
		rebuys = TournamentRebuy.objects.get_rebuys_for_tournament(tournament.id)
		self.assertEqual(len(rebuys), 0)
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(tournament.id)
		self.assertEqual(len(eliminations), 0)

	"""
	bounty_amount can be None if not a bounty tournament.
	"""
	def verify_result(self, result, is_backfill, placement_string, placement_earnings, rebuy_count, eliminations_count, buyin_amount, bounty_amount):
		if bounty_amount == None:
			bounty_amount = 0
		expected_investment = round(buyin_amount + (buyin_amount * rebuy_count), 2)
		expected_bounty_earnings = round(bounty_amount * eliminations_count, 2)
		expected_placement_earnings = placement_earnings
		expected_gross_earnings = round(expected_placement_earnings + expected_bounty_earnings, 2)
		rebuys = TournamentRebuy.objects.get_rebuys_for_player(
			player = result.player
		)
		eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
			player_id = result.player.id
		)
		self.assertEqual(result.investment, expected_investment)
		self.assertEqual(build_placement_string(result.placement), placement_string)
		self.assertEqual(result.placement_earnings, expected_placement_earnings)
		self.assertEqual(len(rebuys), rebuy_count)
		self.assertEqual(result.bounty_earnings, expected_bounty_earnings)
		self.assertEqual(result.gross_earnings, expected_gross_earnings)
		self.assertEqual(len(eliminations), eliminations_count)
		self.assertEqual(result.net_earnings, round(expected_gross_earnings - Decimal(expected_investment), 2))
		self.assertEqual(result.is_backfill, is_backfill)

	def setUp(self):
		# Build some users for the tests
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)

	"""
	Verify cannot use a TournamentStructure that you didn't create.
	"""
	def test_cannot_use_structure_you_dont_own(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Try to create a tournment where the admin is dog using the structure made by cat
		dog = User.objects.get_by_username("dog")
		with self.assertRaisesMessage(ValidationError, "You cannot use a Tournament Structure that you don't own."):
			self.build_tournament(
				admin = dog,
				title = "Doge Tournament",
				structure = structure
			)

	"""
	Verify creating a tournment
	"""
	def test_create_tournament(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		tournaments = Tournament.objects.get_by_user(user = cat)
		self.assertEqual(len(tournaments), 1)
		self.assertEqual(tournaments[0].admin, cat)
		self.assertEqual(tournaments[0].title, "Cat Tournament")
		self.assertEqual(tournaments[0].tournament_structure.buyin_amount, 100)
		self.assertEqual(tournaments[0].tournament_structure.bounty_amount, 10)
		self.assertEqual(tournaments[0].tournament_structure.payout_percentages, [100])
		self.assertEqual(tournaments[0].tournament_structure.allow_rebuys, False)

		# Verify the admin is added as a TournamentPlayer
		players = TournamentPlayer.objects.get_tournament_players(tournaments[0].id)
		self.assertEqual(len(players), 1)
		self.assertEqual(players[0].user, cat)

		# Create a second Tournament with a different structure
		structure2 = self.build_structure(
			user = cat,
			buyin_amount = 199,
			bounty_amount = None,
			payout_percentages = [60, 20, 15, 5],
			allow_rebuys = True
		)
		self.build_tournament(
			title = "Cat Tournament 2",
			admin = cat,
			structure = structure2
		)

		touraments2 = Tournament.objects.get_by_user(user = cat)
		self.assertEqual(len(touraments2), 2)
		self.assertEqual(touraments2[1].admin, cat)
		self.assertEqual(touraments2[1].title, "Cat Tournament 2")
		self.assertEqual(touraments2[1].tournament_structure.buyin_amount, 199)
		self.assertEqual(touraments2[1].tournament_structure.bounty_amount, None)
		self.assertEqual(touraments2[1].tournament_structure.payout_percentages, [60, 20, 15, 5])
		self.assertEqual(touraments2[1].tournament_structure.allow_rebuys, True)

		# Verify the admin is added as a TournamentPlayer
		players2 = TournamentPlayer.objects.get_tournament_players(touraments2[1].id)
		self.assertEqual(len(players2), 1)
		self.assertEqual(players2[0].user, cat)


	"""
	Verify is_completable without rebuys enabled.
	"""
	def test_is_completable_without_rebuys(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# is_completable will raise at this point b/c no one is eliminated
		with self.assertRaisesMessage(ValidationError, "Every player must be eliminated before completing a Tournament"):
			is_completable = Tournament.objects.is_completable(
				tournament_id = tournament.id
			)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Eliminate every player except cat and dog.
		for player in players:
			if player != cat_player and player.user.username != "dog": 
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)

		# is_completable will raise at this point b/c 2 players remain
		with self.assertRaisesMessage(ValidationError, "Every player must be eliminated before completing a Tournament"):
			is_completable = Tournament.objects.is_completable(
				tournament_id = tournament.id
			)

		# Eliminate the last player ("dog")
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		for player in players:
			if player.user.username == "dog":
				eliminate_player(
					tournament_id = tournament.id,
					eliminator_id = cat_player.id,
					eliminatee_id = player.id
				)

		# is_completable will succeed now
		is_completable = Tournament.objects.is_completable(
				tournament_id = tournament.id
			)
		self.assertEqual(is_completable, True)


	"""
	Verify cannot complete a Tournament if not the admin.
	"""
	def test_cannot_complete_tournament_if_not_admin(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate all the players except 1 (cat)
		eliminate_all_players_except(
			players = players,
			except_player = cat_player,
			tournament = tournament
		)

		# Loop through players and try to complete the Tournament. Only the admin will succeed
		for player in players:
			if player.user.username == "cat":
				tournament = Tournament.objects.complete_tournament(
					user = player.user,
					tournament_id = tournament.id
				)
				self.assertTrue(tournament.completed_at != None)
			else:
				with self.assertRaisesMessage(ValidationError, "You cannot update a Tournament if you're not the admin."):
					Tournament.objects.complete_tournament(
						user = player.user,
						tournament_id = tournament.id
					)

	"""
	Verify can't complete a Tournament that has not been started.
	"""
	def test_cannot_complete_tournament_if_not_started(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)
		with self.assertRaisesMessage(ValidationError, "You can't complete a Tournament that has not been started."):
			eliminate_players_and_complete_tournament(admin = cat, tournament = tournament)


	"""
	Verify can't complete a Tournament that is already completed
	"""
	def test_cannot_complete_tournament_if_already_completed(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)
		# Attempt to complete again
		with self.assertRaisesMessage(ValidationError, "This tournament is already completed."):
			Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

	"""
	Verify undo completion cannot be executed if not admin
	"""
	def test_cannot_undo_completion_if_not_admin(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		# Attempt to undo completion if not admin
		for user in User.objects.all():
			if user.username != "cat":
				with self.assertRaisesMessage(ValidationError, "You cannot update a Tournament if you're not the admin."):
					Tournament.objects.undo_complete_tournament(
						user = user,
						tournament_id = tournament.id
				)

	"""
	Verify undo completion if Tournament is not complete.
	"""
	def test_cannot_undo_completion_if_not_admin(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Attempt to undo completion when it has never been completed
		with self.assertRaisesMessage(ValidationError, "The tournament is not completed. Nothing to undo."):
			Tournament.objects.undo_complete_tournament(
					user = cat,
					tournament_id = tournament.id
				)	


	"""
	Verify undo completion deletes eliminations and rebuys
	"""
	def test_undo_completion_deletes_eliminations_rebuys_and_results(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate all the players except 1 (cat)
		eliminate_all_players_except(
			players = players,
			except_player = cat_player,
			tournament = tournament
		)

		# Rebuy on all players (except admin)
		for player in players:
			if player != cat_player:
				rebuy_for_test(
					tournament_id = tournament.id,
					player_id = player.id
				)

		# Eliminate everyone again (Except admin)
		eliminate_all_players_except(
			players = players,
			except_player = cat_player,
			tournament = tournament
		)

		# Verify every player has 2 eliminations (Except cat)
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(
			tournament_id = tournament.id
		)
		elim_dict = {}
		for elimination in eliminations:
			if elimination.eliminatee.id in elim_dict.keys():
				elim_dict[elimination.eliminatee.id] = elim_dict[elimination.eliminatee.id] + 1
			else:
				elim_dict[elimination.eliminatee.id] = 1
		self.assertFalse(cat_player.id in elim_dict)
		for key in elim_dict.keys():
			self.assertEqual(elim_dict[key], 2)

		# Verify every player has 1 rebuy (except cat)
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		for player in players:
			num_rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			if player != cat_player:
				self.assertEqual(len(num_rebuys), 1)
			else:
				self.assertEqual(len(num_rebuys), 0)

		# verify there are no tournament results
		tournament_results = TournamentPlayerResult.objects.get_results_for_tournament(tournament.id)
		self.assertTrue(len(tournament_results) == 0)

		# Complete tournament
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		# verify the tournament results were generated.
		tournament_results = TournamentPlayerResult.objects.get_results_for_tournament(tournament.id)
		self.assertTrue(len(tournament_results) != 0)

		# Undo completion
		Tournament.objects.undo_complete_tournament(
			user = cat,
			tournament_id = tournament.id
		)

		# verify there are no tournament results
		tournament_results = TournamentPlayerResult.objects.get_results_for_tournament(tournament.id)
		self.assertTrue(len(tournament_results) == 0)

		# Verify the eliminations are deleted
		eliminations = TournamentElimination.objects.get_eliminations_by_tournament(
			tournament_id = tournament.id
		)
		self.assertEqual(len(eliminations), 0)

		# Verify rebuys are deleted
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		)
		for player in players:
			num_rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			self.assertEqual(len(num_rebuys), 0)

		# Verify completed_at is None
		tournament = Tournament.objects.get_by_id(tournament.id)
		self.assertEqual(tournament.completed_at, None)

	"""
	Verify cannot start a Tournament unless you're the admin.
	"""
	def test_cannot_start_tournament_if_not_admin(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Cannot start if not admin
		for user in User.objects.all():
			if user.username != "cat":
				with self.assertRaisesMessage(ValidationError, "You cannot update a Tournament if you're not the admin."):
					Tournament.objects.start_tournament(
							user = user,
							tournament_id = tournament.id
						)

	"""
	Verify cannot start a Tournament that's been completed
	"""
	def test_cannot_start_tournament_if_completed(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		# Cannot start if completed
		with self.assertRaisesMessage(ValidationError, "You can't start a Tournament that has already been completed."):
			Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)


	"""
	Verify start_tournament
	"""
	def test_start_tournament(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Verify the state is ACTIVE
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)
		tournament = Tournament.objects.get_by_id(tournament.id)
		self.assertEqual(tournament.get_state(), TournamentState.ACTIVE)

	"""
	Verify cannot calculate tournament value until tournament is complete
	"""
	def test_cannot_calculate_tournament_value_until_complete(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = 10,
			payout_percentages = [100],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		with self.assertRaisesMessage(ValidationError, "Tournament value cannot be calculated until a Tournament is complete."):
			Tournament.objects.calculate_tournament_value(tournament_id = tournament.id, num_rebuys=0)


	"""
	Verify tournament value calculation
	"""
	def test_tournament_value(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = 11.7,
			payout_percentages = [100],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)
		# Eliminate all the players except 1 (cat)
		eliminate_all_players_except(
			players = players,
			except_player = cat_player,
			tournament = tournament
		)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		# Verify the value
		value = Tournament.objects.calculate_tournament_value(tournament_id = tournament.id, num_rebuys=0)
		expected_value = round(Decimal(1036.80), 2)
		self.assertEqual(value, expected_value)

		# undo_complete to add some rebuys. This will reset all eliminations so we need to add again.
		Tournament.objects.undo_complete_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate all the players except 1 (cat)
		eliminate_all_players_except(
			players = players,
			except_player= cat_player,
			tournament = tournament
		)

		# Rebuy on all players (except admin)
		for player in players:
			if player.user.username != "cat":
				rebuy_for_test(
					tournament_id = tournament.id,
					player_id = player.id
				)
		# Eliminate everyone again (Except admin)
		eliminate_all_players_except(
			players = players,
			except_player = cat_player,
			tournament = tournament
		)

		# Complete again
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		# Verify the value
		value = Tournament.objects.calculate_tournament_value(tournament_id = tournament.id, num_rebuys = 8)
		expected_value = round(Decimal(1958.40), 2)
		self.assertEqual(value, expected_value)

	"""
	Verify completing a tournament for backfill is successful.
	Bounties: Enabled
	Rebuys: Enabled
	"""
	def test_complete_tournament_for_backfill_bounty_enabled_rebuy_enabled(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = 11.7,
			payout_percentages = [50, 30, 20],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# --- Placements ----
		player_tournament_placements = [
			# First
			PlayerTournamentPlacement(
				player_id = 1,
				placement = 0,
			),

			# Second
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 1,
			),

			# Third
			PlayerTournamentPlacement(
				player_id = 6,
				placement = 2,
			),
		]

		# --- Eliminations ---
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("id")
		elim_dict = {
			# cat eliminates player3, player4, player5
			1: [players[2], players[3], players[4]],

			# player2 eliminates player9 (twice), player1, player4, player6
			2: [players[8], players[0], players[3], players[8], players[5]],

			# player5 eliminates player7, player6, player2
			5: [players[6], players[5], players[1]],

			# player7 eliminates player8
			7: [players[7]],

			# player8 eliminates player1
			8: [players[0]],

			# player9 eliminates player7
			9: [players[6]],
		}

		# Execute the backfill
		Tournament.objects.complete_tournament_for_backfill(
			user = tournament.admin,
			tournament_id = tournament.id,
			player_tournament_placements = player_tournament_placements,
			elim_dict = elim_dict
		)

		results = TournamentPlayerResult.objects.get_results_for_tournament(
			tournament_id = tournament.id
		)

		buyin_amount = Decimal(115.20)
		bounty_amount = Decimal(11.70)
		for result in results:
			self.assertEqual(result.is_backfill, True)
			if result.player.id == 9:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "2nd",
					placement_earnings = Decimal("465.75"),
					rebuy_count = 1,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 8:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 7:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 1,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 6:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "3rd",
					placement_earnings = Decimal("310.50"),
					rebuy_count = 1,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 5:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 3,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 4:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 1,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 3:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 2:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 5,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 1:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "1st",
					placement_earnings = Decimal("776.25"),
					rebuy_count = 2,
					eliminations_count = 3,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)

	"""
	Verify completing a tournament for backfill is successful.
	Bounties: Disabled
	Rebuys: Enabled
	"""
	def test_complete_tournament_for_backfill_success_bounty_disabled_rebuy_enabled(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = None,
			payout_percentages = [50, 30, 20],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# --- Placements ----
		player_tournament_placements = [
			# First
			PlayerTournamentPlacement(
				player_id = 1,
				placement = 0,
			),

			# Second
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 1,
			),

			# Third
			PlayerTournamentPlacement(
				player_id = 6,
				placement = 2,
			),
		]

		# --- Eliminations ---
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("id")
		elim_dict = {
			# cat eliminates player3, player4, player5
			1: [players[2], players[3], players[4]],

			# player2 eliminates player9 (twice), player1, player4, player6
			2: [players[8], players[0], players[3], players[8], players[5]],

			# player5 eliminates player7, player6, player2
			5: [players[6], players[5], players[1]],

			# player7 eliminates player8
			7: [players[7]],

			# player8 eliminates player1
			8: [players[0]],

			# player9 eliminates player7
			9: [players[6]],
		}

		# Execute the backfill
		Tournament.objects.complete_tournament_for_backfill(
			user = tournament.admin,
			tournament_id = tournament.id,
			player_tournament_placements = player_tournament_placements,
			elim_dict = elim_dict
		)

		results = TournamentPlayerResult.objects.get_results_for_tournament(
			tournament_id = tournament.id
		)

		buyin_amount = Decimal(115.20)
		bounty_amount = None
		# 1728
		for result in results:
			self.assertEqual(result.is_backfill, True)
			if result.player.id == 9:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "2nd",
					placement_earnings = Decimal("518.40"),
					rebuy_count = 1,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 8:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 7:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 1,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 6:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "3rd",
					placement_earnings = Decimal("345.60"),
					rebuy_count = 1,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 5:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 3,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 4:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 1,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 3:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 2:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 5,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 1:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "1st",
					placement_earnings = Decimal("864"),
					rebuy_count = 2,
					eliminations_count = 3,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)

	"""
	Verify completing a tournament for backfill is successful.
	Bounties: Disabled
	Rebuys: Disabled
	"""
	def test_complete_tournament_for_backfill_success_bounty_disabled_rebuy_disabled(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = None,
			payout_percentages = [50, 30, 20],
			allow_rebuys = False
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# --- Placements ----
		player_tournament_placements = [
			# First
			PlayerTournamentPlacement(
				player_id = 1,
				placement = 0,
			),

			# Second
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 1,
			),

			# Third
			PlayerTournamentPlacement(
				player_id = 6,
				placement = 2,
			),
		]

		# --- Eliminations ---
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("id")
		elim_dict = {
			1: [players[2], players[4]],
			2: [players[8], players[3],  players[5]],
			5: [],
			7: [players[7], players[1]],
			8: [],
			9: [players[6]],
		}

		# Execute the backfill
		Tournament.objects.complete_tournament_for_backfill(
			user = tournament.admin,
			tournament_id = tournament.id,
			player_tournament_placements = player_tournament_placements,
			elim_dict = elim_dict
		)

		results = TournamentPlayerResult.objects.get_results_for_tournament(
			tournament_id = tournament.id
		)

		buyin_amount = Decimal(115.20)
		bounty_amount = None
		# 1036.80
		for result in results:
			self.assertEqual(result.is_backfill, True)
			if result.player.id == 9:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "2nd",
					placement_earnings = Decimal("311.04"),
					rebuy_count = 0,
					eliminations_count = 1,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 8:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 7:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 2,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 6:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "3rd",
					placement_earnings = Decimal("207.36"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 5:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 4:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 3:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 0,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 2:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "--",
					placement_earnings = Decimal("0.00"),
					rebuy_count = 0,
					eliminations_count = 3,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)
			elif result.player.id == 1:
				self.verify_result(
					result = result,
					is_backfill = True,
					placement_string = "1st",
					placement_earnings = Decimal("518.40"),
					rebuy_count = 0,
					eliminations_count = 2,
					buyin_amount = buyin_amount,
					bounty_amount = bounty_amount
				)

	"""
	Verify if placements aren't added correctly this fails.
	"""
	def test_complete_tournament_error_placements_not_added(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = 11.7,
			payout_percentages = [50, 30, 20],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# --- Placements ----
		player_tournament_placements = [
			# First
			PlayerTournamentPlacement(
				player_id = 1,
				placement = 0,
			),

			# Second
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 1,
			),

			# Missing third placement!
		]

		# --- Eliminations ---
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("id")
		elim_dict = {
			# cat eliminates player3, player4, player5
			1: [players[2], players[3], players[4]],

			# player2 eliminates player9 (twice), player1, player4, player6
			2: [players[8], players[0], players[3], players[8], players[5]],

			# player5 eliminates player7, player6, player2
			5: [players[6], players[5], players[1]],

			# player7 eliminates player8
			7: [players[7]],

			# player8 eliminates player1
			8: [players[0]],

			# player9 eliminates player7
			9: [players[6]],
		}

		with self.assertRaisesMessage(ValidationError, "The tournament structure requires you select 3 players who placed in the tournament."):
			Tournament.objects.complete_tournament_for_backfill(
				user = tournament.admin,
				tournament_id = tournament.id,
				player_tournament_placements = player_tournament_placements,
				elim_dict = elim_dict
			)
		self.verify_tournament_reset(tournament.id)

	"""
	Verify if the same player is specified for multiple placements, we fail.
	"""
	def test_complete_tournament_error_same_player_multiple_placements(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = 11.7,
			payout_percentages = [50, 30, 20],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# --- Placements ----
		player_tournament_placements = [
			# First
			PlayerTournamentPlacement(
				player_id = 1,
				placement = 0,
			),

			# Second
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 1,
			),

			# Third (SAME PLAYER AS second)
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 2,
			),
		]

		# --- Eliminations ---
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("id")
		elim_dict = {
			# cat eliminates player3, player4, player5
			1: [players[2], players[3], players[4]],

			# player2 eliminates player9 (twice), player1, player4, player6
			2: [players[8], players[0], players[3], players[8], players[5]],

			# player5 eliminates player7, player6, player2
			5: [players[6], players[5], players[1]],

			# player7 eliminates player8
			7: [players[7]],

			# player8 eliminates player1
			8: [players[0]],

			# player9 eliminates player7
			9: [players[6]],
		}

		with self.assertRaisesMessage(ValidationError, "You can't specify the same player for multiple placements."):
			Tournament.objects.complete_tournament_for_backfill(
				user = tournament.admin,
				tournament_id = tournament.id,
				player_tournament_placements = player_tournament_placements,
				elim_dict = elim_dict
			)
		self.verify_tournament_reset(tournament.id)

	"""
	Verify if a player did not win, they were eliminated at least once.
	"""
	def test_complete_tournament_error_if_player_did_not_win_must_be_eliminated(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")
		buyin_amount = 115.20
		structure = self.build_structure(
			user = cat,
			buyin_amount = buyin_amount,
			bounty_amount = 11.7,
			payout_percentages = [50, 30, 20],
			allow_rebuys = True
		)

		# Create tournament
		tournament = self.build_tournament(
			title = "Cat Tournament",
			admin = cat,
			structure = structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		cat_player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			tournament_id = tournament.id,
			user_id = cat.id
		)

		# --- Placements ----
		player_tournament_placements = [
			# First
			PlayerTournamentPlacement(
				player_id = 1,
				placement = 0,
			),

			# Second
			PlayerTournamentPlacement(
				player_id = 9,
				placement = 1,
			),

			# Third
			PlayerTournamentPlacement(
				player_id = 3,
				placement = 2,
			),
		]

		# --- Eliminations ---
		players = TournamentPlayer.objects.get_tournament_players(
			tournament_id = tournament.id
		).order_by("id")
		elim_dict = {
			# cat eliminates player3, player4, player5
			1: [players[2], players[3], players[4]],

			# player2 eliminates player9 (twice), player1, player4, player6
			2: [players[8], players[0], players[3], players[8], players[5]],

			# player5 eliminates player7, player6, player2
			5: [players[6], players[5], players[1]],

			7: [],

			# player8 eliminates player1
			8: [players[0]],

			# player9 eliminates player7
			9: [players[6]],
		}

		# Note: players[7] was never eliminated and they did not win. So error will throw.
		with self.assertRaisesMessage(ValidationError, f"{players[7].user.username} did not win, they must have been eliminated at least once."):
			Tournament.objects.complete_tournament_for_backfill(
				user = tournament.admin,
				tournament_id = tournament.id,
				player_tournament_placements = player_tournament_placements,
				elim_dict = elim_dict
			)
		self.verify_tournament_reset(tournament.id)
		


class TournamentPlayerResultTestCase(TransactionTestCase):

	# Reset primary keys after each test function run
	reset_sequences = True
	
	"""
	bounty_amount: If None, this is not a bounty tournament.
	"""
	def build_structure(self, user, buyin_amount, bounty_amount, payout_percentages, allow_rebuys):
		structure = build_structure(
			admin = user,
			buyin_amount = buyin_amount,
			bounty_amount = bounty_amount,
			payout_percentages = payout_percentages,
			allow_rebuys = allow_rebuys
		)
		return structure
	
	def build_tournament(self, admin, title, structure):
		tournament = Tournament.objects.create_tournament(
			title = title,
			user = admin,
			tournament_structure = structure
		)
		return tournament

	def build_placement_percentages(num_placements):
		if num_placements > 9:
			raise ValidationError("Can't build payout_percentages for tournament with more than 9 players.")
		percentages = []
		for x in range(1, num_placements):
			if x == 1:
				percentages.append(100)
			elif x == 2:
				percentages.append(60,40)
			elif x == 3:
				percentages.append(50,30,20)
		return percentages

	"""
	Builds a dictionary of PlayerPlacementData.
	Their placement is the key and PlayerPlacementData is the value.
	This makes it much easier to verify the placements and earnings.
	"""
	def build_placement_dict(self, is_backfill, tournament, eliminatee_order, eliminator_order, debug=False):
		players = TournamentPlayer.objects.get_tournament_players(tournament.id)
		placement_dict = {}

		for player in players:
			# This will return a queryset but it should only be length of 1.
			result = TournamentPlayerResult.objects.get_results_for_user_by_tournament(
				user_id = player.user.id,
				tournament_id = tournament.id
			)[0]

			self.assertEqual(result.is_backfill, is_backfill)

			eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
				player_id = player.id
			)
			rebuys = TournamentRebuy.objects.get_rebuys_for_player(
				player = player
			)
			placement_data = PlayerPlacementData(
				user_id = result.player.user.id,
				placement = result.placement,
				placement_earnings = f"{result.placement_earnings}",
				investment = f"{result.investment}",
				eliminations = eliminations,
				bounty_earnings = f"{result.bounty_earnings}",
				rebuys = rebuys,
				gross_earnings = f"{result.gross_earnings}",
				net_earnings = f"{result.net_earnings}"
			)
			placement_dict[result.placement] = placement_data

		# For debugging
		if debug:
			for place in placement_dict.keys():
				print(f"{placement_dict[place].user_id} " +
					f"placed {placement_dict[place].placement} " +
					f"and earned {placement_dict[place].placement_earnings}.")

		return placement_dict

	def setUp(self):
		# Build some users for the tests
		users = create_users(
			identifiers = ["cat", "dog", "monkey", "bird", "donkey", "elephant", "gator", "insect", "racoon"]
		)

	"""
	Verify cannot generate results before tournament is completed.
	"""
	def test_cannot_generate_results_before_tournament_complete(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = None,
			payout_percentages = [100],
			allow_rebuys = False
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		with self.assertRaisesMessage(ValidationError, "You cannot build Tournament results until the Tournament is complete."):
			results = TournamentPlayerResult.objects.build_results_for_tournament(tournament.id)

	"""
	Verify cannot calculate placement until tournament completed.
	"""
	def test_cannot_calculate_placement_until_tournament_completed(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = None,
			payout_percentages = [100],
			allow_rebuys = False
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		with self.assertRaisesMessage(ValidationError, "Cannot determine placement until tourment is completed."):
			results = TournamentPlayerResult.objects.determine_placement(user_id=cat.id, tournament_id=tournament.id)


	"""
	Verify placement is calculated correctly.
	No rebuys.
	"""
	def test_placement_calculation_no_rebuys_scenario1(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = None,
			payout_percentages = [100],
			allow_rebuys = False
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate in a specific order so we can verify. 6 is the winner here.
		# These arrays are the primary keys of the users.
		# 5 elim 7, 3 elim 5, 2 elim 3, etc...
		# So expected placement order is: [6, 4, 8, 9, 1, 2, 3, 5, 7]
		eliminatee_order = [7, 5, 3, 2, 1, 9, 8, 4]
		eliminator_order = [5, 3, 2, 1, 9, 8, 4, 6]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order
		)

		self.assertEqual(len(placement_dict), 9) # There were only 9 players
		self.assertEqual(placement_dict[0].user_id, 6)
		self.assertEqual(placement_dict[1].user_id, 4)
		self.assertEqual(placement_dict[2].user_id, 8)
		self.assertEqual(placement_dict[3].user_id, 9)
		self.assertEqual(placement_dict[4].user_id, 1)
		self.assertEqual(placement_dict[5].user_id, 2)
		self.assertEqual(placement_dict[6].user_id, 3)
		self.assertEqual(placement_dict[7].user_id, 5)
		self.assertEqual(placement_dict[8].user_id, 7)

	"""
	Verify placement is calculated correctly.
	No rebuys.
	"""
	def test_placement_calculation_no_rebuys_scenario2(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = None,
			payout_percentages = [100],
			allow_rebuys = False
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the users.
		# 5 elim 7, 9 elim 5, 9 elim 3, etc...
		# So expected placement order is: [9, 6, 8, 4, 5, 3, 2, 1, 7]
		eliminatee_order = [7, 1, 2, 3, 5, 4, 8, 6]
		eliminator_order = [5, 9, 9, 9, 9, 9, 4, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order
		)

		self.assertEqual(len(placement_dict), 9) # There were only 9 players
		self.assertEqual(placement_dict[0].user_id, 9)
		self.assertEqual(placement_dict[1].user_id, 6)
		self.assertEqual(placement_dict[2].user_id, 8)
		self.assertEqual(placement_dict[3].user_id, 4)
		self.assertEqual(placement_dict[4].user_id, 5)
		self.assertEqual(placement_dict[5].user_id, 3)
		self.assertEqual(placement_dict[6].user_id, 2)
		self.assertEqual(placement_dict[7].user_id, 1)
		self.assertEqual(placement_dict[8].user_id, 7)

	"""
	Verify placement is calculated correctly.
	With rebuys.
	"""
	def test_placement_calculation_with_rebuys_scenario1(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 100,
			bounty_amount = None,
			payout_percentages = [100],
			allow_rebuys = True
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Manunally add some rebuys
		# These are the player_id's of the players who rebought.
		# So 1 has two rebuys. 5, 7 and 8 have one rebuy each.
		rebuys = [1, 5, 7, 8, 1]
		for player_id in rebuys:
			rebuy_for_test(
				tournament_id = tournament.id,
				player_id = player_id
			)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the users.
		# 2 elim 1, 5 elim 1, 9 elim 5, 7 elim 2, etc...
		# So expected placement order is: [9, 7, 8, 1, 5, 6, 4, 3, 2]
		eliminatee_order = [1, 1, 5, 2, 3, 4, 6, 5, 7, 8, 1, 8, 7]
		eliminator_order = [2, 5, 9, 7, 8, 1, 1, 9, 8, 1, 9, 7, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order,
			debug = False
		)

		self.assertEqual(len(placement_dict), 9) # There were only 9 players
		self.assertEqual(placement_dict[0].user_id, 9)
		self.assertEqual(placement_dict[1].user_id, 7)
		self.assertEqual(placement_dict[2].user_id, 8)
		self.assertEqual(placement_dict[3].user_id, 1)
		self.assertEqual(placement_dict[4].user_id, 5)
		self.assertEqual(placement_dict[5].user_id, 6)
		self.assertEqual(placement_dict[6].user_id, 4)
		self.assertEqual(placement_dict[7].user_id, 3)
		self.assertEqual(placement_dict[8].user_id, 2)

	"""
	Verify placement earnings is calculated correctly.
	No rebuys, no bounties. (60, 30, 20) payout percentages.
	"""
	def test_placement_earnings_no_rebuys_no_bounties_60_30_20(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 115.12,
			bounty_amount = None,
			payout_percentages = [60, 30, 10],
			allow_rebuys = False
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the users.
		# 5 elim 7, 9 elim 5, 9 elim 3, etc...
		# So expected placement order is: [9, 6, 8, 4, 5, 3, 2, 1, 7]
		eliminatee_order = [7, 1, 2, 3, 5, 4, 8, 6]
		eliminator_order = [5, 9, 9, 9, 9, 9, 4, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order
		)

		self.assertEqual(placement_dict[0].placement_earnings, f"{round(Decimal(621.65), 2)}")
		self.assertEqual(placement_dict[1].placement_earnings, f"{round(Decimal(310.82), 2)}")
		self.assertEqual(placement_dict[2].placement_earnings, f"{round(Decimal(103.61), 2)}")
		self.assertEqual(placement_dict[3].placement_earnings, "0.00")
		self.assertEqual(placement_dict[4].placement_earnings, "0.00")
		self.assertEqual(placement_dict[5].placement_earnings, "0.00")
		self.assertEqual(placement_dict[6].placement_earnings, "0.00")
		self.assertEqual(placement_dict[7].placement_earnings, "0.00")
		self.assertEqual(placement_dict[8].placement_earnings, "0.00")

	"""
	Verify placement earnings is calculated correctly.
	Rebuys enabled, no bounties. (50, 30, 15, 5) payout percentages.
	"""
	def test_placement_earnings_no_bounties_50_30_15_5(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 115.12,
			bounty_amount = None,
			payout_percentages = [50, 30, 15, 5],
			allow_rebuys = True
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Manunally add some rebuys
		# These are the player_id's of the players who rebought.
		# So 1 has two rebuys. 5, 7 and 8 have one rebuy each.
		rebuys = [1, 5, 7, 8, 1]
		for player_id in rebuys:
			rebuy_for_test(
				tournament_id = tournament.id,
				player_id = player_id
			)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the users.
		# 2 elim 1, 5 elim 1, 9 elim 5, 7 elim 2, etc...
		# So expected placement order is: [9, 7, 8, 1, 5, 6, 4, 3, 2]
		eliminatee_order = [1, 1, 5, 2, 3, 4, 6, 5, 7, 8, 1, 8, 7]
		eliminator_order = [2, 5, 9, 7, 8, 1, 1, 9, 8, 1, 9, 7, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order,
			debug = False
		)

		self.assertEqual(placement_dict[0].placement_earnings, f"{round(Decimal(805.84), 2)}")
		self.assertEqual(placement_dict[1].placement_earnings, f"{round(Decimal(483.50), 2)}")
		self.assertEqual(placement_dict[2].placement_earnings, f"{round(Decimal(241.75), 2)}")
		self.assertEqual(placement_dict[3].placement_earnings, f"{round(Decimal(80.58), 2)}")
		self.assertEqual(placement_dict[4].placement_earnings, "0.00")
		self.assertEqual(placement_dict[5].placement_earnings, "0.00")
		self.assertEqual(placement_dict[6].placement_earnings, "0.00")
		self.assertEqual(placement_dict[7].placement_earnings, "0.00")
		self.assertEqual(placement_dict[8].placement_earnings, "0.00")


	"""
	Verify placement earnings is calculated correctly.
	Rebuys enabled, bounties enabled. (50, 30, 15, 5) payout percentages.
	"""
	def test_placement_earnings_rebuys_and_bounty_enabled_50_30_15_5(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 115.12,
			bounty_amount = 25.69,
			payout_percentages = [50, 30, 15, 5],
			allow_rebuys = True
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Manunally add some rebuys
		# These are the player_id's of the players who rebought.
		# So 1 has two rebuys. 5, 7 and 8 have one rebuy each.
		rebuys = [1, 5, 7, 8, 1]
		for player_id in rebuys:
			rebuy_for_test(
				tournament_id = tournament.id,
				player_id = player_id
			)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the users.
		# 2 elim 1, 5 elim 1, 9 elim 5, 7 elim 2, etc...
		# So expected placement order is: [9, 7, 8, 1, 5, 6, 4, 3, 2]
		eliminatee_order = [1, 1, 5, 2, 3, 4, 6, 5, 7, 8, 1, 8, 7]
		eliminator_order = [2, 5, 9, 7, 8, 1, 1, 9, 8, 1, 9, 7, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order,
			debug = False
		)

		self.assertEqual(placement_dict[0].placement_earnings, f"{round(Decimal(626.01), 2)}")
		self.assertEqual(placement_dict[1].placement_earnings, f"{round(Decimal(375.61), 2)}")
		self.assertEqual(placement_dict[2].placement_earnings, f"{round(Decimal(187.80), 2)}")
		self.assertEqual(placement_dict[3].placement_earnings, f"{round(Decimal(62.60), 2)}")
		self.assertEqual(placement_dict[4].placement_earnings, "0.00")
		self.assertEqual(placement_dict[5].placement_earnings, "0.00")
		self.assertEqual(placement_dict[6].placement_earnings, "0.00")
		self.assertEqual(placement_dict[7].placement_earnings, "0.00")
		self.assertEqual(placement_dict[8].placement_earnings, "0.00")


	"""
	Verify placement earnings is calculated correctly.
	Rebuys disabled, bounties enabled. (50, 30, 15, 5) payout percentages.
	"""
	def test_placement_earnings_rebuys_disabled_and_bounty_enabled_50_30_15_5(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 115.12,
			bounty_amount = 25.69,
			payout_percentages = [50, 30, 15, 5],
			allow_rebuys = False
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the users.
		# 5 elim 7, 9 elim 5, 9 elim 3, etc...
		# So expected placement order is: [9, 6, 8, 4, 5, 3, 2, 1, 7]
		eliminatee_order = [7, 1, 2, 3, 5, 4, 8, 6]
		eliminator_order = [5, 9, 9, 9, 9, 9, 4, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order
		)

		# Verify results
		investment_decimal = Decimal("115.12")
		for place in placement_dict.keys():
			self.assertEqual(placement_dict[place].investment, "115.12")
			self.assertEqual(
				[rebuy.player.id for rebuy in placement_dict[place].rebuys],
				[]
			)
			if placement_dict[place].user_id == 9:
				gross_earnings = placement_dict[place].gross_earnings
				bounty_earnings = Decimal(placement_dict[place].bounty_earnings)
				placement_earnings = Decimal(placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(gross_earnings, f"{round(placement_earnings + bounty_earnings, 2)}")
				self.assertEqual(placement_dict[place].placement_earnings, f"{round(Decimal(402.44), 2)}")
				self.assertEqual(place, 0)
				self.assertEqual(placement_dict[place].bounty_earnings, f"{round(Decimal(154.14), 2)}")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[1, 2, 3, 5, 4, 6]
				)
			elif placement_dict[place].user_id == 8:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].placement_earnings, f"{round(Decimal(120.73), 2)}")
				self.assertEqual(place, 2)
				self.assertEqual(gross_earnings, f"{round(Decimal(120.73), 2)}")
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[]
				)
			elif placement_dict[place].user_id == 7:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, "0.00")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 8)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[]
				)
			elif placement_dict[place].user_id == 6:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].placement_earnings, f"{round(Decimal(241.46), 2)}")
				self.assertEqual(place, 1)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, f"{round(Decimal(241.46), 2)}")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[]
				)
			elif placement_dict[place].user_id == 5:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				bounty_earnings = Decimal(placement_dict[place].bounty_earnings)
				placement_earnings = Decimal(placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 4)
				self.assertEqual(placement_dict[place].bounty_earnings, f"{round(Decimal(25.69), 2)}")
				self.assertEqual(gross_earnings, f"{round(Decimal(25.69), 2)}")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[7]
				)
			elif placement_dict[place].user_id == 4:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				bounty_earnings = Decimal(placement_dict[place].bounty_earnings)
				placement_earnings = Decimal(placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].gross_earnings, f"{round(placement_earnings + bounty_earnings, 2)}")
				self.assertEqual(placement_dict[place].placement_earnings, f"{round(Decimal(40.24), 2)}")
				self.assertEqual(place, 3)
				self.assertEqual(gross_earnings, f"{round(Decimal(65.93), 2)}")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[8]
				)
			elif placement_dict[place].user_id == 3:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, "0.00")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 5)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[]
				)
			elif placement_dict[place].user_id == 2:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, "0.00")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 6)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[]
				)
			elif placement_dict[place].user_id == 1:
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - investment_decimal, 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, "0.00")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 7)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[]
				)

	"""
	Verify placement earnings is calculated correctly.
	Rebuys enabled, bounties enabled. (50, 30, 15, 5) payout percentages.
	"""
	def test_placement_earnings_rebuys_enabled_and_bounty_enabled_50_30_15_5(self):
		# Build a structure made by cat
		cat = User.objects.get_by_username("cat")

		structure = self.build_structure(
			user = cat,
			buyin_amount = 115.12,
			bounty_amount = 25.69,
			payout_percentages = [50, 30, 15, 5],
			allow_rebuys = True
		)

		tournament = self.build_tournament(
			admin = cat,
			title = "Results tournament",
			structure= structure
		)

		# Add players
		players = add_players_to_tournament(
			users = User.objects.all(),
			tournament = tournament
		)

		# Start
		Tournament.objects.start_tournament(user = cat, tournament_id = tournament.id)

		# Manunally add some rebuys
		# These are the player_id's of the players who rebought.
		# So 1 has two rebuys. 5, 7 and 8 have one rebuy each.
		rebuys = [1, 5, 7, 8, 1]
		for player_id in rebuys:
			rebuy_for_test(
				tournament_id = tournament.id,
				player_id = player_id
			)

		tournament_rebuys = TournamentRebuy.objects.get_rebuys_for_tournament(
			tournament_id = tournament.id
		)

		# Eliminate in a specific order so we can verify. 9 is the winner here.
		# These arrays are the primary keys of the players.
		# 2 elim 1, 5 elim 1, 9 elim 5, 7 elim 2, etc...
		# So expected placement order is: [9, 7, 8, 1, 5, 6, 4, 3, 2]
		eliminatee_order = [1, 1, 5, 2, 3, 4, 6, 5, 7, 8, 1, 8, 7]
		eliminator_order = [2, 5, 9, 7, 8, 1, 1, 9, 8, 1, 9, 7, 9]
		for index,eliminatee_id in enumerate(eliminatee_order):
			eliminate_player(
				tournament_id = tournament.id,
				eliminator_id = eliminator_order[index],
				eliminatee_id = eliminatee_id
			)

		# Complete
		Tournament.objects.complete_tournament(user = cat, tournament_id = tournament.id)

		placement_dict = self.build_placement_dict(
			is_backfill = False,
			tournament = tournament,
			eliminatee_order = eliminatee_order,
			eliminator_order = eliminator_order,
			debug = False
		)

		# Verify results
		for place in placement_dict.keys():
			if placement_dict[place].user_id == 9:
				expected_investment = "115.12"
				gross_earnings = placement_dict[place].gross_earnings
				bounty_earnings = Decimal(placement_dict[place].bounty_earnings)
				placement_earnings = Decimal(placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(gross_earnings, f"{round(placement_earnings + bounty_earnings, 2)}")
				self.assertEqual(placement_dict[place].placement_earnings, "626.01")
				self.assertEqual(place, 0)
				self.assertEqual(placement_dict[place].bounty_earnings, "102.76")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[5, 5, 1, 7]
				)
				self.assertEqual(placement_dict[place].investment, "115.12")
				self.assertEqual(len(placement_dict[place].rebuys), 0)
			elif placement_dict[place].user_id == 8:
				expected_investment = "230.24"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(placement_dict[place].placement_earnings, "187.80")
				self.assertEqual(place, 2)
				self.assertEqual(gross_earnings, "239.18")
				self.assertEqual(placement_dict[place].bounty_earnings, "51.38")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[3, 7]
				)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 1)
				self.assertEqual(placement_dict[place].rebuys[0].player.id, 8)
			elif placement_dict[place].user_id == 7:
				expected_investment = "230.24"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(gross_earnings, "426.99")
				self.assertEqual(placement_dict[place].placement_earnings, "375.61")
				self.assertEqual(place, 1)
				self.assertEqual(placement_dict[place].bounty_earnings, "51.38")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[2, 8]
				)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 1)
				self.assertEqual(placement_dict[place].rebuys[0].player.id, 7)
			elif placement_dict[place].user_id == 6:
				expected_investment = "115.12"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(gross_earnings, placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 5)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(len(placement_dict[place].eliminations), 0)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 0)
			elif placement_dict[place].user_id == 5:
				expected_investment = "230.24"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				bounty_earnings = Decimal(placement_dict[place].bounty_earnings)
				placement_earnings = Decimal(placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 4)
				self.assertEqual(placement_dict[place].bounty_earnings, "25.69")
				self.assertEqual(gross_earnings, "25.69")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[1]
				)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 1)
				self.assertEqual(placement_dict[place].rebuys[0].player.id, 5)
			elif placement_dict[place].user_id == 4:
				expected_investment = "115.12"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				bounty_earnings = Decimal(placement_dict[place].bounty_earnings)
				placement_earnings = Decimal(placement_dict[place].placement_earnings)
				self.assertEqual(placement_dict[place].gross_earnings, f"{round(placement_earnings + bounty_earnings, 2)}")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 6)
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(len(placement_dict[place].eliminations), 0)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 0)
			elif placement_dict[place].user_id == 3:
				expected_investment = "115.12"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(placement_dict[place].gross_earnings, "0.00")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 7)
				self.assertEqual(placement_dict[place].bounty_earnings, "0.00")
				self.assertEqual(gross_earnings, "0.00")
				self.assertEqual(len(placement_dict[place].eliminations), 0)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 0)
			elif placement_dict[place].user_id == 2:
				expected_investment = "115.12"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(placement_dict[place].placement_earnings, "0.00")
				self.assertEqual(place, 8)
				self.assertEqual(placement_dict[place].bounty_earnings, "25.69")
				self.assertEqual(gross_earnings, "25.69")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[1]
				)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 0)
			elif placement_dict[place].user_id == 1:
				expected_investment = "345.36"
				gross_earnings = placement_dict[place].gross_earnings
				self.assertEqual(placement_dict[place].net_earnings, f"{round(Decimal(gross_earnings) - Decimal(expected_investment), 2)}")
				self.assertEqual(gross_earnings, "139.67")
				self.assertEqual(placement_dict[place].placement_earnings, "62.60")
				self.assertEqual(place, 3)
				self.assertEqual(placement_dict[place].bounty_earnings, "77.07")
				self.assertEqual(
					[elimination.eliminatee.id for elimination in placement_dict[place].eliminations],
					[4, 6, 8]
				)
				self.assertEqual(placement_dict[place].investment, expected_investment)
				self.assertEqual(len(placement_dict[place].rebuys), 2)
				self.assertEqual(placement_dict[place].rebuys[0].player.id, 1)





		

		

		


















