from django.test import TestCase
from account.models import Account

# Run with 'python manage.py test'
class AccountTestCase(TestCase):

	def setUp(self):
		# Create an account
		Account.objects.create_user(email="test@test.com", username="tester", password='password')

	def test_does_not_create_duplicate_accounts_with_same_email(self):
		# Will throw exception if you try to create account with same email.
		self.assertRaises(ValueError, Account.objects.create_user, email="test@test.com", username="tester2", password='password')

	def test_does_not_create_duplicate_accounts_with_same_email_different_case(self):
		# Will throw exception if you try to create account with same email (different case).
		self.assertRaises(ValueError, Account.objects.create_user, email="tEsT@test.com", username="tester2", password='password')

	def test_does_not_create_duplicate_accounts_with_same_username(self):
		# Should throw exception if you try to create account with same username.
		self.assertRaises(ValueError, Account.objects.create_user, email="test2@test.com", username="tester", password='password')

	def test_does_not_create_duplicate_accounts_with_same_username_different_case(self):
		# Should throw exception if you try to create account with same username (different case).
		self.assertRaises(ValueError, Account.objects.create_user, email="test2@test.com", username="teStEr", password='password')

	def test_get_by_username(self):
		# query the account by username
		account = Account.objects.get_by_username("Tester")
		self.assertEqual(account.email, "test@test.com")

		# Same thing but change case.
		account = Account.objects.get_by_username("TeSteR")
		self.assertEqual(account.email, "test@test.com")

	def test_get_by_email(self):
		# query the account by email
		account = Account.objects.get_by_email("test@test.com")
		self.assertEqual(account.email, "test@test.com")

		# Same thing but change case.
		account = Account.objects.get_by_email("TeSt@tEst.Com")
		self.assertEqual(account.email, "test@test.com")


