from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from tournament.models import Tournament, TournamentPlayer
from tournament_group.forms import CreateTournamentGroupForm
from tournament_group.models import TournamentGroup
from user.models import User

@login_required
def tournament_group_create_view(request, *args, **kwargs):
	context = {}
	try:
		if request.method == 'POST':
			form = CreateTournamentGroupForm(request.POST)
			if form.is_valid():
				tournament_group = TournamentGroup.objects.create_tournament_group(
					admin = request.user,
					title = form.cleaned_data['title'],
				)
				messages.success(request, "Tournament Group Created!")

				return redirect('tournament_group:update', pk=tournament_group.id)
		else:
			form = CreateTournamentGroupForm()
		context['form'] = form
	except Exception as e:
		messages.error(request, e.args[0])
		form = CreateTournamentGroupForm()
		context['form'] = form
	return render(request=request, template_name='tournament_group/create_tournament_group.html', context=context)

@login_required
def tournament_group_update_view(request, *args, **kwargs):
	context = {}
	try:
		pk = kwargs['pk']
		tournament_group = TournamentGroup.objects.get_by_id(pk)
		if tournament_group == None:
			raise ValidationError("Our records indicate that TournamentGroup does not exist.")

		if request.user != tournament_group.admin:
			return redirect("tournament_group:view", pk=tournament_group.id)

		context['tournament_group'] = tournament_group

		current_users = tournament_group.get_users()
		context['current_users'] = current_users

		# Get the updated title
		new_title = request.POST.get("new_title")
		if new_title == None or new_title == "":
			new_title = tournament_group.title
		context['new_title'] = new_title

		if_title_save_btn_enabled = False
		if new_title != tournament_group.title:
			if_title_save_btn_enabled = True
		context['if_title_save_btn_enabled'] = if_title_save_btn_enabled

		# Search for users with htmx
		search = request.GET.get("search")
		if search != None and search != "":
			search_result_users = User.objects.all().filter(username__icontains=search)
			# Exclude the admin,
			search_result_users = search_result_users.exclude(email__iexact=request.user.email)
			# Exclude users who are already added
			for user in current_users:
				search_result_users = search_result_users.exclude(email__iexact=user.email)
			context['search_result_users'] = search_result_users
			context['search'] = search

		current_tournaments = tournament_group.get_tournaments()
		context['current_tournaments'] = current_tournaments

		# Search for tournaments with htmx
		search_tournaments = request.GET.get("search_tournaments")
		if search_tournaments != None and search_tournaments != "":
			tournament_search_result = Tournament.objects.all().filter(title__icontains=search_tournaments)
			
			# Exclude Tournaments that are already added
			for tournament in current_tournaments:
				tournament_search_result = tournament_search_result.exclude(id=tournament.id)

			# Exclude tournaments where none of the users in this group have played.
			for tournament in tournament_search_result:
				if not TournamentGroup.objects.has_at_least_one_user_played_in_tournament(group=tournament_group, tournament=tournament):
					tournament_search_result = tournament_search_result.exclude(id=tournament.id)
			context['tournament_search_result'] = tournament_search_result
			context['search_tournaments'] = search_tournaments

		context['edit_mode'] = True
	except Exception as e:
		messages.error(request, e.args[0])
	return render(request=request, template_name='tournament_group/update_tournament_group.html', context=context)


@login_required
def view_tournament_group(request, *args, **kwargs):
	context = {}
	try:
		pk = kwargs['pk']
		tournament_group = TournamentGroup.objects.get_by_id(pk)
		if tournament_group == None:
			raise ValidationError("Our records indicate that TournamentGroup does not exist.")

		context['tournament_group'] = tournament_group

		users = tournament_group.get_users()
		context['users'] = users

		if request.user not in users:
			return redirect("error", error_message="You are not part of that Tournament Group.")

		tournaments = tournament_group.get_tournaments()
		context['tournaments'] = tournaments

		context['edit_mode'] = False

	except Exception as e:
		messages.error(request, e.args[0])
	return render(request=request, template_name='tournament_group/tournament_group_view.html', context=context)

"""
HTMX request for adding a user to a TournamentGroup.
"""
@login_required
def add_user_to_group(request, *args, **kwargs):
	try:
		user_id = kwargs['user_id']
		tournament_group_id = kwargs['tournament_group_id']

		user = User.objects.get_by_id(user_id)
		tourmament_group = TournamentGroup.objects.get_by_id(tournament_group_id)
		
		TournamentGroup.objects.add_users_to_group(
			admin = request.user,
			group = tourmament_group,
			users = [user]
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect(request.META['HTTP_REFERER'])

"""
HTMX request for removing a user from a TournamentGroup.
"""
@login_required
def remove_user_from_group(request, *args, **kwargs):
	try:
		user_id = kwargs['user_id']
		tournament_group_id = kwargs['tournament_group_id']

		user = User.objects.get_by_id(user_id)
		tourmament_group = TournamentGroup.objects.get_by_id(tournament_group_id)
		
		TournamentGroup.objects.remove_user_from_group(
			admin = request.user,
			group = tourmament_group,
			user = user
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect(request.META['HTTP_REFERER'])

"""
HTMX request for adding a Tournament to a TournamentGroup.
"""
@login_required
def add_tournament_to_group(request, *args, **kwargs):
	try:
		tournament_id = kwargs['tournament_id']
		tournament_group_id = kwargs['tournament_group_id']

		tournament = Tournament.objects.get_by_id(tournament_id)
		tourmament_group = TournamentGroup.objects.get_by_id(tournament_group_id)
		
		TournamentGroup.objects.add_tournaments_to_group(
			admin = request.user,
			group = tourmament_group,
			tournaments = [tournament]
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect(request.META['HTTP_REFERER'])


"""
HTMX request for removing a Tournament to a TournamentGroup.
"""
@login_required
def remove_tournament_from_group(request, *args, **kwargs):
	try:
		tournament_id = kwargs['tournament_id']
		tournament_group_id = kwargs['tournament_group_id']

		tournament = Tournament.objects.get_by_id(tournament_id)
		tourmament_group = TournamentGroup.objects.get_by_id(tournament_group_id)
		
		TournamentGroup.objects.remove_tournament_from_group(
			admin = request.user,
			group = tourmament_group,
			tournament = tournament
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect(request.META['HTTP_REFERER'])

"""
HTMX request for updating the Tournament Group title.
"""
@login_required
def update_tournament_group_title(request, *args, **kwargs):
	try:
		title = kwargs['title']
		tournament_group_id = kwargs['tournament_group_id']

		tourmament_group = TournamentGroup.objects.get_by_id(tournament_group_id)
		
		TournamentGroup.objects.update_tournament_group_title(
			admin = request.user,
			group = tourmament_group,
			title = title
		)
	except Exception as e:
		messages.error(request, e.args[0])
	return redirect(request.META['HTTP_REFERER'])


















