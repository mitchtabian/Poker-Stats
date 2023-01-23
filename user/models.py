from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from user.util import validate_email


class UserManager(BaseUserManager):
	def _create_user(self, email, username, password, is_staff, is_superuser, **extra_fields):
		self.is_email_and_username_valid(email, username)
		now = timezone.now()
		email = email.lower()
		user = self.model(
			email=email,
			username=username,
			is_staff=is_staff, 
			is_active=True,
			is_superuser=is_superuser, 
			last_login=now,
			date_joined=now, 
			**extra_fields
		)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_user(self, email, username, password, **extra_fields):
		self.is_email_and_username_valid(email, username)
		return self._create_user(email, username, password, False, False, **extra_fields)

	def create_superuser(self, email, username, password, **extra_fields):
		self.is_email_and_username_valid(email, username)
		user=self._create_user(email, username, password, True, True, **extra_fields)
		user.save(using=self._db)
		return user

	# Use this to fetch an User by email. This is case-insensitive!
	def get_by_email(self, email):
		try:
			user = self.get(email__iexact=email)
		except User.DoesNotExist:
			user = None
		return user

	# Use this to fetch a user by username. This is case-insensitive!
	def get_by_username(self, username):
		try:
			user = self.get(username__iexact=username)
		except User.DoesNotExist:
			user = None
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

	# Validates the email and username of an user before it's created.
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
class User(AbstractBaseUser, PermissionsMixin):
	email 					= models.EmailField(max_length=254, unique=True)
	username 				= models.CharField(max_length=254, blank=True, unique=True)
	is_staff 				= models.BooleanField(default=False)
	is_superuser 			= models.BooleanField(default=False)
	is_active 				= models.BooleanField(default=True)
	last_login 				= models.DateTimeField(null=True, blank=True)
	date_joined 			= models.DateTimeField(auto_now_add=True)

	USERNAME_FIELD = 'email'
	EMAIL_FIELD = 'email'
	REQUIRED_FIELDS = ['username']

	objects = UserManager()

	def get_absolute_url(self):
		return "/users/%i/" % (self.pk)









