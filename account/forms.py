from account.models import Account
from account.exceptions import EmailAlreadyInUseException
from crispy_forms.layout import Layout, Fieldset, Submit, MultiField, Field, Div
from crispy_forms.helper import FormHelper
from django import forms

class AccountCreationForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Register',
                'email',
                'username',
                'password1',
                'password2',
            ),
            Submit('submit', 'Register', css_class='submit-button'),
        )

    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ('email', 'username')

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")  
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        email = self.cleaned_data.get("email")
        username = self.cleaned_data.get("username")
        try:
            user = Account.objects.create_user(email=email, username=username)
        except Exception as e:
            if len(e.args) > 0:
                if "duplicate key value violates unique constraint" in e.args[0]:
                    raise EmailAlreadyInUseException(email)
            raise forms.ValidationError(e)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user








