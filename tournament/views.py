import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from tournament.forms import CreateTournamentForm, CreateTournamentStructureForm, EditTournamentForm
from tournament.models import Tournament, TournamentStructure, TournamentState, TournamentInvite, TournamentPlayer, TournamentElimination, TournamentPlayerResult
from tournament.util import PlayerTournamentData
from user.models import User

@login_required
def tournament_create_view(request, *args, **kwargs):
	context = {}
	if request.method == 'POST':
		form = CreateTournamentForm(request.POST, user=request.user)
		if form.is_valid():
			tournament = Tournament.objects.create_tournament(
				user = request.user,
				title = form.cleaned_data['title'],
				tournament_structure = form.cleaned_data['tournament_structure'],
			)
			if tournament is not None:
				messages.success(request, "Tournament Created!")

			redirect_url = request.GET.get('next')
			if redirect_url is not None:
				return redirect(redirect_url)
			return redirect("tournament:tournament_view", pk=tournament.id)
	else:
		form = CreateTournamentForm(user=request.user)

	context['form'] = form
	return render(request=request, template_name='tournament/create_tournament.html', context=context)

@login_required
def tournament_list_view(request, *args, **kwargs):
	context = {}
	context['tournaments'] = Tournament.objects.get_by_user(user=request.user)
	return render(request=request, template_name="tournament/tournament_list.html", context=context)

@login_required
def tournament_view(request, *args, **kwargs):
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	return render_tournament_view(request, tournament.id)

@login_required
def start_tournament(request, *args, **kwargs):
	tournament_id = kwargs['pk']
	try:
		user = request.user
		
		# Verify the admin is performing this action
		verify_admin(
			user = user,
			tournament_id = tournament_id,
			error_message = "You are not the admin of this Tournament."
		)

		tournament = Tournament.objects.start_tournament(user=user, tournament_id=tournament_id)

		# Delete all the pending invites
		invites = TournamentInvite.objects.find_pending_invites_for_tournament(tournament.id)
		for invite in invites:
			invite.delete()
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect("tournament:tournament_view", pk=tournament_id)

@login_required
def complete_tournament(request, *args, **kwargs):
	tournament_id = kwargs['pk']
	try:
		user = request.user
		
		# Verify the admin is performing this action
		verify_admin(
			user = user,
			tournament_id = tournament_id,
			error_message = "You are not the admin of this Tournament."
		)

		tournament = Tournament.objects.complete_tournament(user, tournament_id)
	except Exception as e:
		messages.error(request, e.args[0])
	
	return redirect("tournament:tournament_view", pk=tournament_id)

@login_required
def undo_completed_at(request, *args, **kwargs):
	tournament_id = kwargs['pk']
	try:
		user = request.user

		# Verify the admin is performing this action
		verify_admin(
			user = user,
			tournament_id = tournament_id,
			error_message = "You are not the admin of this Tournament."
		)

		Tournament.objects.undo_complete_tournament(
			user = user,
			tournament_id = tournament_id
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect("tournament:tournament_view", pk=tournament_id)

@login_required
def undo_started_at(request, *args, **kwargs):
	tournament_id = kwargs['pk']
	try:
		user = request.user
		# Verify the admin is performing this action
		verify_admin(
			user = user,
			tournament_id = tournament_id,
			error_message = "You are not the admin of this Tournament."
		)

		tournament = Tournament.objects.get_by_id(tournament_id)
		tournament.started_at = None
		tournament.save()
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect("tournament:tournament_view", pk=tournament_id)

"""
Join a Tournament given a TournamentInvite.
kwargs['id'] is the id of the TournamentInvite.
"""
@login_required
def join_tournament(request, *args, **kwargs):
	user = request.user
	try:
		invite = TournamentInvite.objects.get(pk=kwargs['pk'])
		if invite.send_to != user:
			messages.error(request, "This invitation wasn't for you.")
			return redirect("home")

		# Create new TournamentPlayer
		player = TournamentPlayer.objects.create_player_for_tournament(
			user_id = invite.send_to.id,
			tournament_id = invite.tournament.id
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect("tournament:tournament_view", pk=invite.tournament.id)

"""
Uninvite a player from a tournament.
HTMX request for tournament_view
"""
@login_required
def uninvite_player_from_tournament(request, *args, **kwargs):
	user = request.user
	player_id = kwargs['player_id']
	tournament_id = kwargs['tournament_id']
	try:
		TournamentInvite.objects.uninvite_player_from_tournament(
			admin = user,
			uninvite_user_id = player_id,
			tournament_id = tournament
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return render_tournament_view(request, tournament_id)
	

"""
Remove a player from a tournament.
HTMX request for tournament_view
"""
@login_required
def remove_player_from_tournament(request, *args, **kwargs):
	user = request.user
	player_id = kwargs['player_id']
	tournament_id = kwargs['tournament_id']
	try:
		TournamentPlayer.objects.remove_player_from_tournament(
			removed_by_user_id= user.id,
			removed_user_id=player_id,
			tournament_id=tournament_id
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return render_tournament_view(request, tournament_id)

"""
Invite a player to a tournament.
HTMX request for tournament_view
"""
@login_required
def invite_player_to_tournament(request, *args, **kwargs):
	try:
		user = request.user
		player_id = kwargs['player_id']
		tournament_id = kwargs['tournament_id']
		
		# Verify the admin is sending the invite
		verify_admin(
			user = user,
			tournament_id = tournament_id,
			error_message = "Only the admin can invite players."
		)

		invite = TournamentInvite.objects.send_invite(
			sent_from_user_id = user.id,
			send_to_user_id = player_id,
			tournament_id = tournament_id
		)
		return render_tournament_view(request, tournament_id)
	except Exception as e:
		messages.error(request, e.args[0])
	return render_tournament_view(request, tournament_id)

"""
Eliminate a player from a tournament.
Returns a generic HttpResponse with a status code representing whether it was successful or not.
If it was not successful, the user will be redirected to an error page.
"""
@login_required
def eliminate_player_from_tournament(request, *args, **kwargs):
	user = request.user
	try:
		# Who is doing the eliminating
		eliminator_id = kwargs['eliminator_id']

		# Who is being eliminated
		eliminatee_id = kwargs['eliminatee_id']

		# Tournament id where this is taking place
		tournament_id = kwargs['tournament_id']

		# Verify the admin is the one eliminating
		verify_admin(
			user = request.user,
			tournament_id = tournament_id,
			error_message = "Only the admin can eliminate players."
		)

		# All the validation is performed in the create_elimination function.
		elimination = TournamentElimination.objects.create_elimination(
			tournament_id = tournament_id,
			eliminator_id = eliminator_id,
			eliminatee_id = eliminatee_id
		)
	except Exception as e:
		messages.error(request, e.args[0])
		return HttpResponse(content_type='application/json', status=400)
	return HttpResponse(content_type='application/json', status=200)

"""
Rebuy for an eliminated player.
Returns a generic HttpResponse with a status code representing whether it was successful or not.
If it was not successful, the user will be redirected to an error page.
"""
@login_required
def rebuy_player_in_tournament(request, *args, **kwargs):
	try:
		# Who is rebuying
		player_id = kwargs['player_id']

		# Tournament id where this is taking place
		tournament_id = kwargs['tournament_id']

		# Verify the tournament admin is executing the rebuy
		verify_admin(
			user = request.user,
			tournament_id = tournament_id,
			error_message = "Only the admin can execute a rebuy."
		)
	
		# All the validation is performed in the rebuy_by_user_id_and_tournament_id function.
		elimination = TournamentPlayer.objects.rebuy_by_user_id_and_tournament_id(
			tournament_id = tournament_id,
			user_id = player_id,
		)
	except Exception as e:
		messages.error(request, e.args[0])
		return HttpResponse(content_type='application/json', status=400)
	return HttpResponse(content_type='application/json', status=200)

"""
Common function shared between tournament_view and htmx requests used in that view.
"""
def render_tournament_view(request, tournament_id):
	context = {}
	tournament = Tournament.objects.get_by_id(tournament_id)
	context['tournament'] = tournament
	context['tournament_state'] = tournament.get_state()

	# Get all the players that have joined the Tournament. They are a TournamentPlayer
	players = TournamentPlayer.objects.get_tournament_players(tournament.id)
	context['players'] = players

	# Get the pending invites
	invites = TournamentInvite.objects.find_pending_invites_for_tournament(tournament.id)
	context['invites'] = invites
	
	# Search for users with htmx
	search = request.GET.get("search")
	if search != None and search != "":
		users = User.objects.all().filter(username__icontains=search)
		# Exclude the admin,
		users = users.exclude(email__iexact=request.user.email)
		# Exclude pending invites
		for invite in invites:
			users = users.exclude(email__iexact=invite.send_to.email)
		# Exclude users who have already joined
		for player in players:
			users = users.exclude(email__iexact=player.user.email)
		context['users'] = users
		context['search'] = search

	context['is_bounty_tournament'] = tournament.tournament_structure.bounty_amount != None
	context['allow_rebuys'] = tournament.tournament_structure.allow_rebuys
	context['player_tournament_data'] = get_player_tournament_data(tournament_id)

	# If the tournament is completed, send some custom data structures for the results data
	# if tournament.completed_at != None:
	return render(request=request, template_name="tournament/tournament_view.html", context=context)

"""
Retrieve a TournamentStructure and serialize to Json.
TODO("dont need this?")
"""
@login_required
def get_tournament_structure(request):
	structure_id = request.GET['tournament_structure_id']
	if structure_id is not None:
		structure = TournamentStructure.objects.get_by_id(structure_id)
		try:
			return JsonResponse({"structure": f"{structure.buildJson()}"}, status=200)
		except Exception as e:
			return JsonResponse({"error": "Serialization error."}, status=400)
	else:
		return JsonResponse({"error": "Unable to retrieve tournament structure details."}, status=400)

@login_required
def tournament_structure_create_view(request, *args, **kwargs):
	context = {}
	if request.method == 'POST':
		form = CreateTournamentStructureForm(request.POST)
		if form.is_valid():
			payout_percentages = [int(int_percentage) for int_percentage in (form.cleaned_data['hidden_payout_structure'].split(","))]
			tournament_structure = TournamentStructure.objects.create_tournament_struture(
				user = request.user,
				title = form.cleaned_data['title'],
				allow_rebuys = form.cleaned_data['allow_rebuys'],
				buyin_amount = form.cleaned_data['buyin_amount'],
				bounty_amount = form.cleaned_data['bounty_amount'],
				payout_percentages = payout_percentages,
			)

			messages.success(request, "Created new Tournament Structure")

			redirect_url = request.GET.get('next')
			if redirect_url is not None:
				# If they were editing a tournament, make sure to select the new tournament structure when they return.
				if "/tournament/tournament_edit/" in redirect_url:
					redirect_url = f"{redirect_url}?selected_structure_pk={tournament_structure.pk}"
				return redirect(redirect_url)
			form = CreateTournamentStructureForm()

	else:
		form = CreateTournamentStructureForm()

	context['form'] = form
	return render(request=request, template_name='tournament/create_tournament_structure.html', context=context)

@login_required
def tournament_edit_view(request, *args, **kwargs):
	context = {}
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	state = tournament.get_state()
	if state == TournamentState.ACTIVE or state == TournamentState.ACTIVE:
		messages.error(request, "You can't edit a Tournament that is completed or active.")
		return redirect("tournament:tournament_view", pk=tournament.id)
	if request.method == 'POST':
		form = EditTournamentForm(request.POST, user=request.user, tournament_pk=tournament.id)
		if form.is_valid():
			tournament.tournament_structure = form.cleaned_data['tournament_structure']
			tournament.title = form.cleaned_data['title']
			tournament.save()

			messages.success(request, "Tournament Updated!")

			return redirect("tournament:tournament_view", pk=tournament.id)
	else:
		form = EditTournamentForm(user=request.user, tournament_pk=tournament.id)
	context['form'] = form
	context['tournament_pk'] = tournament.id
	initial_selected_structure = tournament.tournament_structure
	seleted_structure_pk_from_kwargs = None

	# Check if we are returning from creating a new structure. If we are, select that structure.
	try:
		seleted_structure_pk_from_kwargs = request.GET.get('selected_structure_pk')
	except Exception as e:
		pass
	if seleted_structure_pk_from_kwargs != None:
		initial_selected_structure = TournamentStructure.objects.get_by_id(seleted_structure_pk_from_kwargs)
	context['initial_selected_structure'] = initial_selected_structure

	# Add all TournamentStructure's for this user so we can populate a table when one is selected.
	context['tournament_structures'] = TournamentStructure.objects.get_structures_by_user(request.user)
	return render(request=request, template_name='tournament/tournament_edit_view.html', context=context)

@login_required
def tournament_admin_view(request, *args, **kwargs):
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	return render_tournament_admin_view(request, tournament.id)



"""
Convenience function for the htmx functions that happen on tournament_admin_view.
"""
@login_required
def render_tournament_admin_view(request, tournament_id):
	context = {}
	tournament = Tournament.objects.get_by_id(tournament_id)
	if tournament.get_state() != TournamentState.ACTIVE:
		messages.error(request, "Admin view is not available until Tournament is activated.")
		return redirect("tournament:tournament_view", pk=tournament.id)
	if request.user != tournament.admin:
		messages.error(request, "You are not the Tournament admin.")
		return redirect("tournament:tournament_view", pk=tournament.id)

	context['tournament_state'] = tournament.get_state()
	context['tournament'] = tournament
	context['is_bounty_tournament'] = tournament.tournament_structure.bounty_amount != None
	context['allow_rebuys'] = tournament.tournament_structure.allow_rebuys
	context['player_tournament_data'] = get_player_tournament_data(tournament_id)
	return render(request=request, template_name="tournament/tournament_admin_view.html", context=context)

"""
Builds a list of PlayerTournamentData.
"""
def get_player_tournament_data(tournament_id):
	player_tournament_data = []
	players = TournamentPlayer.objects.get_tournament_players(tournament_id)
	for player in players:
		eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
			tournament_id = tournament_id,
			eliminator_id = player.user.id
		)
		is_eliminated = TournamentElimination.objects.is_player_eliminated(
			user_id = player.user.id,
			tournament_id = tournament_id
		)
		data = PlayerTournamentData(
					user_id = player.user.id,
					username = player.user.username,
					rebuys = player.num_rebuys,
					bounties = len(eliminations),
					is_eliminated = is_eliminated
				)
		player_tournament_data.append(data)
	return player_tournament_data

"""
Convenience function for verifying the admin is the one trying to do something.
If it is not the admin, raise ValidationError using error_message.
"""
def verify_admin(user, tournament_id, error_message):
	tournament = Tournament.objects.get_by_id(tournament_id)
	if user != tournament.admin:
		raise ValidationError(error_message)



















