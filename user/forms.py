from django import forms

from user.models import User

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']