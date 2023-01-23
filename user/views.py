from allauth.account.views import PasswordChangeView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect

from django.urls import reverse
from django.views.generic.edit import UpdateView

from user.forms import UserUpdateForm
from user.models import User

"""
Overrides the PasswordChangeView from django-allauth so that it redirects to home
after the password has been changed.
"""
class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
	def get_success_url(self, **kwargs):
		user = self.request.user
		if  user.is_authenticated:
			return reverse('user:profile', args=(user.pk,))
		else:
			return reverse('home')

class UserProfileView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
	template_name = 'user/profile.html'
	model = User
	form_class = UserUpdateForm
	success_message = 'Profile updated'

	def get_success_url(self):
		return reverse('user:profile', kwargs={'pk': self.get_object().id})

	# Do not allow users to view a profile that is not theres.
	def test_func(self):
		this_user = self.get_object()
		if self.request.user == this_user:
			return True
		return False

	def handle_no_permission(self):
		return redirect('user:cannot_edit_others_profile')

user_profile_view = login_required(UserProfileView.as_view())

def cannot_edit_others_profile(request):
	return render(request=request, template_name="user/cannot_edit_someone_elses_profile.html", context={})