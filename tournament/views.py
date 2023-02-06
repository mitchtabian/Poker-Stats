from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from tournament.forms import CreateTournamentForm, CreateTournamentStructureForm
from tournament.models import Tournament, TournamentStructure


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
			form = CreateTournamentForm(user=request.user)
	else:
		form = CreateTournamentForm(user=request.user)

	context['form'] = form
	return render(request=request, template_name='tournament/create_tournament.html', context=context)

@login_required
def tournament_list_view(request, *args, **kwargs):
	context = {}
	context['tournaments'] = Tournament.objects.get_by_user(user=request.user)
	return render(request=request, template_name="tournament/tournament_list.html", context=context)

"""
TODO
1) request to join tournament feature?
"""
@login_required
def tournament_view(request, *args, **kwargs):
	context = {}
	context['tournament'] = Tournament.objects.get_by_id(kwargs['pk'])
	return render(request=request, template_name="tournament/tournament_view.html", context=context)

@login_required
def start_tournament(request, *args, **kwargs):
	user = request.user
	tournament = Tournament.objects.get_by_id(kwargs['pk'])
	if tournament.admin != user:
		messages.warning(request, "You are not the admin of this Tournament.")
	tournament.started_at = timezone.now()
	tournament.save()
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
				return redirect(redirect_url)
			form = CreateTournamentStructureForm()

	else:
		form = CreateTournamentStructureForm()

	context['form'] = form
	return render(request=request, template_name='tournament/create_tournament_structure.html', context=context)















