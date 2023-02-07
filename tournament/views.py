import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from tournament.forms import CreateTournamentForm, CreateTournamentStructureForm, EditTournamentForm
from tournament.models import Tournament, TournamentStructure, TournamentState, TournamentInvite, TournamentPlayer
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
	user = request.user
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	if tournament.admin != user:
		messages.warning(request, "You are not the admin of this Tournament.")
	tournament.started_at = timezone.now()
	tournament.save()

	# Delete all the pending invites
	invites = TournamentInvite.objects.find_pending_invites_for_tournament(tournament.id)
	for invite in invites:
		invite.delete()

	return redirect("tournament:tournament_view", pk=kwargs['pk'])

@login_required
def complete_tournament(request, *args, **kwargs):
	user = request.user
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	if tournament.admin != user:
		messages.warning(request, "You are not the admin of this Tournament.")
	tournament.completed_at = timezone.now()
	tournament.save()
	return redirect("tournament:tournament_view", pk=kwargs['pk'])

@login_required
def undo_completed_at(request, *args, **kwargs):
	user = request.user
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	if tournament.admin != user:
		messages.warning(request, "You are not the admin of this Tournament.")
	tournament.completed_at = None
	tournament.save()
	return redirect("tournament:tournament_view", pk=kwargs['pk'])

@login_required
def undo_started_at(request, *args, **kwargs):
	user = request.user
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	if tournament.admin != user:
		messages.warning(request, "You are not the admin of this Tournament.")
	tournament.started_at = None
	tournament.save()
	return redirect("tournament:tournament_view", pk=kwargs['pk'])

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

		try:
			# Create new TournamentPlayer
			player = TournamentPlayer.objects.create_player_for_tournament(
				user_id = invite.send_to.id,
				tournament_id = invite.tournament.id
			)
			player.save()

			# Delete the invite
			invite.delete()
		except Exception as e:
			# Delete the invite
			invite.delete()
			messages.error(request, e.args[0])
			return redirect("home")
		return redirect("tournament:tournament_view", pk=invite.tournament.id)
	except TournamentInvite.DoesNotExist:
		messages.error(request, "Tournament does not exist.")
	return redirect("home")

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
		invite = TournamentInvite.objects.find_pending_invites(
			send_to_user_id=player_id,
			tournament_id=tournament_id
		)

		# Verify the admin is trying to remove the invite
		tournament = Tournament.objects.get_by_id(tournament_id)
		if tournament.admin != user:
			messages.error(request, "Only the admin can remove invites.")
			return render_tournament_view(request, tournament_id)

		invite.delete()
	except TournamentInvite.DoesNotExist:
		error_message = "That player does not have an invite to this tournament."
		messages.error(request, error_message)
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
		player = TournamentPlayer.objects.get_tournament_player_by_user_id(
			user_id=player_id,
			tournament_id=tournament_id
		)

		# Verify the admin is trying to remove the user OR the authenticated user is removing themself.
		tournament = Tournament.objects.get_by_id(tournament_id)
		if tournament.admin != user and user.id != player_id:
			messages.error(request, "Only the admin can remove players.")
		else:
			player.delete()

	except TournamentPlayer.DoesNotExist:
		error_message = "That player is not part of this tournament."
		messages.error(request, error_message)
	return render_tournament_view(request, tournament_id)

"""
Invite a player to a tournament.
HTMX request for tournament_view
"""
@login_required
def invite_player_to_tournament(request, *args, **kwargs):
	user = request.user
	player_id = kwargs['player_id']
	tournament_id = kwargs['tournament_id']
	try:
		# Verify the admin is sending the invite
		tournament = Tournament.objects.get_by_id(tournament_id)
		if tournament.admin != user:
			messages.error(request, "Only the admin can invite players.")
			return render_tournament_view(request, tournament_id)

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

def tournament_admin_view(request, *args, **kwargs):
	context = {}
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	context['tournament'] = tournament
	return render(request=request, template_name="tournament/tournament_admin_view.html", context=context)












