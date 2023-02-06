from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.urls import reverse
from django.utils.safestring import mark_safe

from tournament.models import TournamentStructure, Tournament
from tournament.strings import (
	bounty_amount_exceeds_buyin_amount_error,
	percentages_must_be_a_number,
	percentages_must_be_greater_than_0,
	percentages_must_not_be_empty,
	percentages_must_sum_to_100,
	this_number_cannot_be_negative,
	this_number_must_be_greater_than_0,
	you_must_enter_a_bounty_amount,
	you_must_enter_a_buyin_amount,
	you_must_enter_a_payout_structure,
)

class TournamentStructureWidgetCanAdd(widgets.Select):

	def __init__(self, related_model, related_url=None, *args, **kw):
		super(TournamentStructureWidgetCanAdd, self).__init__(*args, **kw)
		if not related_url:
			rel_to = related_model
			info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
			related_url = '/'

		# Be careful that here "reverse" is not allowed
		self.related_url = related_url

	def render(self, name, value, *args, **kwargs):
		output = [super(TournamentStructureWidgetCanAdd, self).render(name, value, *args, **kwargs)]
		output.append(u'<a href="%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
		(self.related_url, name))
		output.append(u'Add new Tournament Structure</a>')                                                                                                                              
		return mark_safe(u''.join(output))


class CreateTournamentForm(forms.Form):
	title 						= forms.CharField()
	tournament_structure 		= forms.ModelChoiceField(
									queryset=None,
									widget=TournamentStructureWidgetCanAdd(
										TournamentStructure,
										related_url="/tournament/create_tournament_structure/?next=/tournament/create_tournament/"
									)
								)

	class Meta:
		model = Tournament
		fields = ('title', 'tournament_structure')

	def __init__(self, *args, **kwargs):
		self.user = kwargs.pop('user', None)
		super(CreateTournamentForm, self).__init__(*args, **kwargs)
		self.fields['tournament_structure'].queryset = TournamentStructure.objects.get_structures_by_user(self.user)


class CreateTournamentStructureForm(forms.Form):
	title 						= forms.CharField(label="Title", required=True, initial="")
	buyin_amount		 		= forms.IntegerField(label="Buyin amount", required=True)
	allow_rebuys		 		= forms.BooleanField(label="Allow rebuys", required=False, initial=False)
	is_bounty_tournament		= forms.BooleanField(label="Is bounty tournament", required=False, initial=False)
	bounty_amount		 		= forms.IntegerField(label="Bounty amount", required=False)
	hidden_payout_structure		= forms.CharField(label="Payout structure")

	def clean_buyin_amount(self):
		buyin_amount = self.cleaned_data.get('buyin_amount')
		if buyin_amount is None:
			self.add_error("buyin_amount", you_must_enter_a_buyin_amount)
		if buyin_amount <= 0:
			self.add_error("buyin_amount", this_number_must_be_greater_than_0)
		return buyin_amount

	def clean_bounty_amount(self):
		# bounty is less than buyin amount
		buyin_amount = self.cleaned_data.get('buyin_amount')
		bounty_amount = self.cleaned_data.get('bounty_amount')
		is_bounty_tournament = self.cleaned_data.get('is_bounty_tournament')
		if is_bounty_tournament:
			if bounty_amount is None:
				self.add_error("bounty_amount", you_must_enter_a_bounty_amount)
			elif bounty_amount <= 0:
				self.add_error("bounty_amount", this_number_must_be_greater_than_0)
			else:
				if bounty_amount >= buyin_amount:
					self.add_error("bounty_amount", bounty_amount_exceeds_buyin_amount_error)
		return bounty_amount

	def clean_hidden_payout_structure(self):
		payout_structure_raw = self.cleaned_data.get('hidden_payout_structure')
		if payout_structure_raw is None:
			self.add_error("hidden_payout_structure", you_must_enter_a_payout_structure)
		percentages = payout_structure_raw.split(",")
		pct_sum = 0
		for percentage in percentages:
			if percentage is None:
				self.add_error("hidden_payout_structure", percentages_must_not_be_empty)
			try:
				pct_sum += int(percentage)
				if int(percentage) <= 0:
					self.add_error("hidden_payout_structure", percentages_must_be_greater_than_0)
			except Exception as e:
				self.add_error("hidden_payout_structure", percentages_must_be_a_number)
		if pct_sum != 100:
			self.add_error("hidden_payout_structure", percentages_must_sum_to_100)
		return payout_structure_raw


































