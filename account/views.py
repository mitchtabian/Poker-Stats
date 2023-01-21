from account.forms import AccountCreationForm, AccountLoginForm
from account.models import Account
from account.strings import (
	account_with_email_does_not_exist,
	error_unsuccessful_registration,
	invalid_email_or_password,
	login_success,
	password_is_incorrect,
	registration_successful,
)
from account.util import validate_email
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from verify_email.email_handler import send_verification_email


"""
Views
"""

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


"""
Login will not (authenticate) if the email has not been verified. If the user tries to login before
they're verified, they'll see a message telling them to check their email.
"""
def login_view(request):
	if request.method == "POST":
		form = AccountLoginForm(request, data=request.POST)

		"""
		Before validating the form:
		(1) Check if this user even exists.
		(2) If it exists, check if their email if verified. 
		"""
		try:
			email = request.POST['username']
			validate_email(email)
			if email is not None:
				is_verified = is_email_verified(email)
				if not is_verified:
					return redirect("request-new-link-from-email")
		except ValueError as e:
			messages.error(request, e.args[0])
			return return_login_form(request, AccountLoginForm(form))

		# Continue, the user exists and is verified.
		if form.is_valid():
			email = form.cleaned_data.get('username')
			password = form.cleaned_data.get('password')
			user = authenticate(email=email, password=password)
			if user is not None:
				login(request, user)
				messages.info(request, login_success(user))
				return redirect("home")
			# An unknown error occurred
			else:
				messages.error(request, form.errors.as_data())
				return return_login_form(request, form)
		# The only way the form can be invalid at this point is if the password is wrong.
		else:
			messages.error(request, password_is_incorrect)
			return return_login_form(request, form)
	return return_login_form(request, AccountLoginForm())


"""
Utility
"""
def is_email_verified(email):
	account = Account.objects.get_by_email(email=email)
	if account is not None:
		return account.is_active
	raise ValueError(account_with_email_does_not_exist(email))

def return_registration_form(request, form):
	return render(request=request, template_name='account/register.html', context={"register_form": form})

def return_login_form(request, form):
	return render(request=request, template_name="account/login.html", context={"login_form":form})








