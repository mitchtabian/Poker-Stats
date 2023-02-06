from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.edit import FormView, CreateView
from django.views.generic.detail import DetailView

from tournament.forms import CreateTournamentForm, CreateTournamentStructureForm
from tournament.models import Tournament, TournamentStructure


class TournamentCreateView(LoginRequiredMixin, SuccessMessageMixin, FormView):
	template_name = 'tournament/create_tournament.html'
	form_class = CreateTournamentForm
	success_message = 'Tournament Created'

	def get_success_url(self):
		return reverse('tournament:create_tournament')

	def form_valid(self, form):
		user = self.request.user
		form.instance.admin = user
		return super().form_valid(form)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		form = CreateTournamentForm()
		user = self.request.user
		form.fields['tournament_structure'].queryset = TournamentStructure.objects.get_structures_by_user(user)
		context['form'] = form
		return context

"""
TODO
Add login required mixin
Add authenticated required mixin?
"""
def tournament_structure_create_view(request):
	context = {}
	# if this is a POST request we need to process the form data
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = CreateTournamentStructureForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			payout_percentages = [int(int_percentage) for int_percentage in (form.cleaned_data['hidden_payout_structure'].split(","))]
			tournament_structure = TournamentStructure.objects.create_tournament_struture(
				user = request.user, # TODO(add login required mixin or whatever)
				title = form.cleaned_data['title'],
				allow_rebuys = form.cleaned_data['allow_rebuys'],
				buyin_amount = form.cleaned_data['buyin_amount'],
				bounty_amount = form.cleaned_data['bounty_amount'],
				payout_percentages = payout_percentages,
			)

			messages.success(request, "Created new Tournament Structure")

			# TODO(redirect using next?)

	# if a GET (or any other method) we'll create a blank form
	else:
		form = CreateTournamentStructureForm()

	context['form'] = form
	return render(request=request, template_name='tournament/create_tournament_structure.html', context=context)















