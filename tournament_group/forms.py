from django import forms

from tournament_group.models import TournamentGroup

class CreateTournamentGroupForm(forms.ModelForm):
    class Meta:
        model = TournamentGroup
        fields = ['title']