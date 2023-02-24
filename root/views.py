from django.shortcuts import render, redirect, reverse
from django.utils import timezone
from decimal import Decimal

from tournament.models import (
	TournamentInvite,
	TournamentPlayer,
	TournamentState,
	TournamentElimination,
	TournamentRebuy,
	TournamentSplitElimination
)
from tournament_analytics.models import TournamentTotals

from tournament.util import get_value_or_default

def root_view(request):
	try:
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

			# Build rebuys and eliminations graph
			tournament_players = sorted(
				tournament_players,
				key=lambda x: get_value_or_default(x.tournament.completed_at, timezone.now()),
				reverse=False
				)
			rebuys_and_eliminations_dict = {}
			for player in tournament_players:
				if player.tournament.completed_at != None:
					eliminations = TournamentElimination.objects.get_eliminations_by_eliminator(
						player_id = player.id
					)
					split_eliminations = TournamentSplitElimination.objects.get_split_eliminations_by_eliminator(
						player_id = player.id
					)
					split_eliminations_count = 0
					for split_elimination in split_eliminations:
						eliminators = split_elimination.eliminators.all()
						split_eliminations_count += 1.00 / len(eliminators)
					rebuys = TournamentRebuy.objects.get_rebuys_for_player(
						player = player
					)
					rebuys_and_eliminations_dict[f"{player.tournament.completed_at}"] = {
						'eliminations': round(Decimal(len(eliminations) + split_eliminations_count), 2),
						'rebuys': len(rebuys),
						'tournament_title': player.tournament.title,
						'completed_at': player.tournament.completed_at
					}
			if rebuys_and_eliminations_dict:
				context['rebuys_and_eliminations'] = rebuys_and_eliminations_dict

			return render(request, "root/root.html", context=context)
		else:
			return redirect("/accounts/login/")
	except Exception as e:
		messages.error(request, e.args[0])
		return render(request, "root/root.html", context={})
	

def contact_view(request):
	return render(request, "root/contact.html")

def error_view(request, *args, **kwargs):
	message = kwargs['error_message']
	context = {}
	context['message'] = message
	return render(request=request, template_name="root/error.html", context=context)