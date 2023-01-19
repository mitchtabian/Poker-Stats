from account.forms import AccountCreationForm
from account.strings import (
	error_unsuccessful_registration,
	invalid_email_or_password,
	login_success,
	registration_successful,
)
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from verify_email.email_handler import send_verification_email

"""
Upon successfull registration an email will be sent to verify their account. When the user clicks
the link in their email, the account will be active by marking is_active=true.
"""
def register_view(request):
	if request.method == "POST":
		form = AccountCreationForm(request.POST)
		if form.is_valid():
			try:
				inactive_user = send_verification_email(request, form)
			except Exception as e:
				if len(e.args) > 0:
					messages.error(request, e.args[0])
				return return_registration_form(request, form)
			messages.success(request, registration_successful)
			return redirect("home")
		messages.error(request, error_unsuccessful_registration)
		return return_registration_form(request, form)
	form = AccountCreationForm()
	return return_registration_form(request, form)

def return_registration_form(request, form):
	return render(request=request, template_name='account/register.html', context={"register_form": form})

"""
Note: Login will will (authenticate) if the email has not been verified.
"""
def login_view(request):
	if request.method == "POST":
		form = AuthenticationForm(request, data=request.POST)
		if form.is_valid():
			email = form.cleaned_data.get('username')
			password = form.cleaned_data.get('password')
			# TODO(figure out if they've verified their email and is_active is therefore true)
			# If not, will need to show "resend email" form.
			user = authenticate(email=email, password=password)
			if user is not None:
				login(request, user)
				messages.info(request, login_success(user))
				return redirect("home")
			else:
				messages.error(request, invalid_email_or_password)
		else:
			messages.error(request, invalid_email_or_password)
	form = AuthenticationForm()
	return render(request=request, template_name="account/login.html", context={"login_form":form})




