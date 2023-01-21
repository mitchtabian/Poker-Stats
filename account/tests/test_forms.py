from django.forms import ValidationError
from django.test import TestCase

from account.forms import AccountCreationForm
from account.strings import passwords_dont_match_error

class AccountCreationFormTest(TestCase):

	def test_form_fields(self):
		form = AccountCreationForm()

		# Verify labels
		self.assertTrue(form.fields['email'].label == 'Email')
		self.assertTrue(form.fields['username'].label == 'Username')
		self.assertTrue(form.fields['password1'].label == 'Password')
		self.assertTrue(form.fields['password2'].label == 'Password confirmation')

		# Verify help text
		self.assertTrue(form.fields['email'].help_text == '')
		self.assertTrue(form.fields['username'].help_text == '')
		self.assertTrue(form.fields['password1'].help_text == '')
		self.assertTrue(form.fields['password2'].help_text == '')

	def test_passwords_dont_match(self):
		data = {
			'email': 'test@test.com',
			'username': 'tester',
			'password1': 'password',
			'password2': 'somethingelse'
		}
		form = AccountCreationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertEqual(form.errors.as_data()['password2'][0], ValidationError(passwords_dont_match_error))

	def test_email_required(self):
		data = {
			'email': '',
			'username': 'tester',
			'password1': 'password',
			'password2': 'password'
		}
		form = AccountCreationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertTrue(type(form.errors.as_data()['email'][0]), type(ValidationError))
		self.assertTrue(form.errors.as_data()['email'][0].args[0], "This field is required.")

	def test_username_required(self):
		data = {
			'email': 'test@test.com',
			'username': '',
			'password1': 'password',
			'password2': 'password'
		}
		form = AccountCreationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertTrue(type(form.errors.as_data()['username'][0]), type(ValidationError))
		self.assertTrue(form.errors.as_data()['username'][0].args[0], "This field is required.")

	def test_password1_required(self):
		data = {
			'email': 'test@test.com',
			'username': 'tester',
			'password1': '',
			'password2': 'password'
		}
		form = AccountCreationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertTrue(type(form.errors.as_data()['password1'][0]), type(ValidationError))
		self.assertTrue(form.errors.as_data()['password1'][0].args[0], "This field is required.")

	def test_password2_required(self):
		data = {
			'email': 'test@test.com',
			'username': 'tester',
			'password1': 'password',
			'password2': ''
		}
		form = AccountCreationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertTrue(type(form.errors.as_data()['password2'][0]), type(ValidationError))
		self.assertTrue(form.errors.as_data()['password2'][0].args[0], "This field is required.")






















