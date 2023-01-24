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

# def tournament_structure_create_view(request):
# 	context = {}
# 	context['form'] = CreateTournamentStructureForm()
# 	return render(request=request, template_name='tournament/create_tournament_structure.html', context=context)



class TournamentStructureCreateView(LoginRequiredMixin, SuccessMessageMixin, FormView):
	template_name = 'tournament/create_tournament_structure.html'
	form_class = CreateTournamentStructureForm
	success_message = 'Tournament Structure Created'

	def get_success_url(self):
		return reverse('tournament:create_tournament_structure')

	def form_valid(self, form):
		user = self.request.user
		form.instance.user = user
		return super().form_valid(form)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		form = CreateTournamentStructureForm()
		user = self.request.user
		# form.fields['tournament_structure'].queryset = TournamentStructure.objects.get_structures_by_user(user)
		context['form'] = form
		return context


# class TournamentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
 
# 	model = Tournament
# 	template_name = 'tournament/create_tournament.html'
# 	fields = ['title', 'tournament_structure']
# 	success_message = 'Tournament Created'

# 	def get_success_url(self):
# 		return reverse('tournament:create_tournament')

# 	def get_form(self,  *args, **kwargs):
# 		form = super(TournamentCreateView, self).get_form(*args, **kwargs)
# 		user = self.request.user
# 		form.fields['tournament_structure'].queryset = TournamentStructure.objects.get_structures_by_user(user)
# 		return form
	
# 	def form_valid(self, form):
# 		user = self.request.user
# 		form.instance.admin = user
# 		return super(TournamentCreateView, self).form_valid(form)












