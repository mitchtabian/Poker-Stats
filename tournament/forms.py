from django import forms
from django.forms import widgets
from django.urls import reverse
from django.utils.safestring import mark_safe


from tournament.models import TournamentStructure, Tournament

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
		self.related_url = reverse(self.related_url)
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
										related_url="tournament:create_tournament_structure"
									)
								)


class PercentageWidgetCanAdd(widgets.NumberInput):

	def __init__(self, related_model, related_url=None, *args, **kw):
		super(PercentageWidgetCanAdd, self).__init__(*args, **kw)
		if not related_url:
			rel_to = related_model
			info = (rel_to._meta.app_label, rel_to._meta.object_name.lower())
			related_url = '/'

		# Be careful that here "reverse" is not allowed
		self.related_url = related_url

	def render(self, name, value, *args, **kwargs):
		self.related_url = reverse(self.related_url)
		output = [super(PercentageWidgetCanAdd, self).render(name, value, *args, **kwargs)]
		output.append(u'<a href="%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
		(self.related_url, name))
		output.append(u'Add another position</a>')                                                                                                                              
		return mark_safe(u''.join(output))

PERCENTAGE_CHOICES = list(str(i*5) for i in range(1, 20))

def get_percentage_field_name(position):
	if position == 1:
		return "First place"
	if position == 2:
		return "Second place"
	if position == 3:
		return "Third place"
	else:
		return "dunno"

class CreateTournamentStructureForm(forms.Form):
	title 						= forms.CharField()
	buyin_amount		 		= forms.IntegerField()
	bounty_amount		 		= forms.IntegerField()
	allow_rebuys		 		= forms.BooleanField()
	# payout_percentages			= forms.MultipleChoiceField(choices = PERCENTAGE_CHOICES)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# TODO(set label somehow? "Pay Structure")
		field_name = get_percentage_field_name(1)
		self.fields[field_name] = forms.IntegerField(
			required=False,
			widget=PercentageWidgetCanAdd(
				int,
				related_url="tournament:create_tournament_structure"
			)
		)
		self.fields[field_name].label = field_name
		self.fields[field_name].initial = 100
		# for i in range(1, len(PERCENTAGE_CHOICES)):
		# 	field_name = get_percentage_field_name(i)
		# 	self.fields[field_name] = forms.IntegerField(required=False)
		# 	self.fields[field_name].label = field_name
		# 	self.fields[field_name].initial = 100
			# try:
			# 	self.initial[field_name] = PERCENTAGE_CHOICES[i]
			# except IndexError:
			# 	self.initial[field_name] = ""
		# create an extra blank field
		# field_name = f'percentage_{i + 1,}'
		# self.fields[field_name] = forms.CharField(required=False)

	def clean(self):
		percentages = set()
		i = 0
		field_name = f'percentage_{i,}'
		while self.cleaned_data.get(field_name):
			percentage = self.cleaned_data[field_name]
			if percentage in percentages:
				self.add_error(field_name, 'Duplicate')
			else:
				percentages.add(percentage)
			i += 1
			field_name = f'percentage_{i,}'
		self.cleaned_data['percentages'] = percentages

	def save(self):
		# tournament_structure = self.instance
		# tournament_structure.title = self.cleaned_data['title']
		# tournament_structure.buyin_amount = self.cleaned_data['buyin_amount']
		# tournament_structure.bounty_amount = self.cleaned_data['bounty_amount']
		# tournament_structure.allow_rebuys = self.cleaned_data['allow_rebuys']

		print(f"percentages: {self.cleaned_data['percentages']}")
		# tournament_structure.payout_percentages = list()
		# tournament_structure.save()

		structure = TournamentStructure.objects.create_tournament_struture(
			title=self.cleaned_data['title'],
			buyin_amount=self.cleaned_data['buyin_amount'],
			bounty_amount=self.cleaned_data['bounty_amount'],
			allow_rebuys=self.cleaned_data['allow_rebuys'],
			payout_percentages=listOf(60,20,20)
		)
		print(f"structure: {structure}")


























