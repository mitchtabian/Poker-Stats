from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from account.util import validate_email


class AccountManager(BaseUserManager):
	# Use this to fetch an account by email. This is case-insensitive!
	def get_by_email(self, email):
		try:
			account = self.get(email__iexact=email)
		except Account.DoesNotExist:
			account = None
		return account

	# Use this to fetch an account by username. This is case-insensitive!
	def get_by_username(self, username):
		try:
			account = self.get(username__iexact=username)
		except Account.DoesNotExist:
			account = None
		return account

	def create_user(self, email, username, password=None):
		self.is_email_and_username_valid(email, username)

		user = self.model(
			email=email.lower(),
			username=username,
		)

		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, email, username, password):
		self.is_email_and_username_valid(email, username)

		user = self.create_user(
			email=email.lower(),
			password=password,
			username=username,
		)
		user.is_admin = True
		user.save(using=self._db)
		return user

	# Throws exception if a username is already in use by another user.
	def check_username_does_not_exist(self, username):
		user = self.get_by_username(username)
		if user:
			raise ValueError(f'{username} is already taken by another user.')
		else:
			return username

	def check_email_does_not_exist(self, email):
		user = self.get_by_email(email)
		if user:
			raise ValueError(f'{email} is already taken by another user.')
		else:
			return email

	# Validates the email and username of an account before it's created.
	# Returns True if the email and username are available and valid.
	def is_email_and_username_valid(self, email, username):
		if not email:
			raise ValueError('Users must have an email address.')

		# Validate the email address. Will throw exception if not valid format.
		validate_email(email)

		if not username:
			raise ValueError('Users must have a username.')

		# Verify the email is not already taken.
		self.check_email_does_not_exist(email.lower())

		# Verify the username is not already taken.
		self.check_username_does_not_exist(username)

		return True

"""
is_active: False if email is not verified.
"""
class Account(AbstractBaseUser):
	email					= models.EmailField(verbose_name='email', max_length=60, unique=True)
	username				= models.CharField(verbose_name="username", max_length=30, unique=True)
	is_admin				= models.BooleanField(default=False)
	is_staff				= models.BooleanField(default=False)
	is_active				= models.BooleanField(default=False)
	date_joined				= models.DateTimeField(verbose_name='date joined', auto_now_add=True)
	last_login				= models.DateTimeField("last login", blank=True, null=True)

	USERNAME_FIELD			= 'email'
	REQUIRED_FIELDS			= ['username']
	objects					= AccountManager()

	class Meta:
		verbose_name = "Account"
		verbose_name_plural = "Accounts"

	def __str__(self):
		return self.email

	def has_perm(self, perm, obj=None):
		return self.is_admin

	def has_module_perms(self, app_label):
		"Does the user have permissions to view the app `app_label`?"
		# Simplest possible answer: Yes, always
		return True

	def is_staff(self):
		if self.is_admin:
			return True
		return self.is_staff

