from django.shortcuts import render

from tournament.models import TournamentInvite, TournamentPlayer,TournamentState

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

	return render(request, "root/root.html", context=context)

def contact_view(request):
	return render(request, "root/contact.html")

def error_view(request, *args, **kwargs):
	message = kwargs['error_message']
	context = {}
	context['message'] = message
	return render(request=request, template_name="root/error.html", context=context)