from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from account.forms import AccountCreationForm

def register_view(request):
	if request.method == "POST":
		form = AccountCreationForm(request.POST)
		if form.is_valid():
			try:
				user = form.save()
			except Exception as e:
				if len(e.args) > 0:
					messages.error(request, e.args[0])
				return return_registration_form(request, form)
			login(request, user)
			messages.success(request, "Registration successful." )
			return redirect("home")
		messages.error(request, "Unsuccessful registration. Invalid information.")
		return return_registration_form(request, form)
	form = AccountCreationForm()
	return return_registration_form(request, form)

def return_registration_form(request, form):
	return render(request=request, template_name='account/register.html', context={"register_form": form})