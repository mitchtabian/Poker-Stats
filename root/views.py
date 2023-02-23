from django.shortcuts import render, redirect, reverse

from tournament.models import TournamentInvite, TournamentPlayer,TournamentState
from tournament_analytics.models import TournamentTotals

def root_view(request):
	user = request.user
	context = {}
	if user.is_authenticated:
		invites = TournamentInvite.objects.find_pending_invites_for_user(user.id)
		for invite in invites:
			if invite.tournament.get_state() == TournamentState.COMPLETED:
				invites = invites.exclude(tournament=invite.tournament)
		context['invites'] = invites

		# get all the Tournaments that this user has joined
		tournament_players = TournamentPlayer.objects.get_all_tournament_players_by_user_id(user.id)
		tournaments = []
		for player in tournament_players:
			tournaments.append(player.tournament)
		context['tournaments'] = tournaments

		# Get TournamentTotals
		tournament_totals = TournamentTotals.objects.get_or_build_tournament_totals_by_user_id(user_id = user.id)
		tournament_totals = sorted(tournament_totals, key=lambda x: x.timestamp, reverse=False)
		context['tournament_totals'] = tournament_totals

		return render(request, "root/root.html", context=context)
	else:
		return redirect("/accounts/login/")

def contact_view(request):
	return render(request, "root/contact.html")

def error_view(request, *args, **kwargs):
	message = kwargs['error_message']
	context = {}
	context['message'] = message
	return render(request=request, template_name="root/error.html", context=context)