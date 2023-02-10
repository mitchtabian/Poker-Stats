from user.models import User

"""
Utility function for building User objects.

Ex: If 'identifier' == 'cat', it will produce: User(email="cat@cat.com", username="cat", password="password)
"""
def build_user(identifier):
	return User.objects.create_user(
			email=f"{identifier}@{identifier}.com",
			username=f"{identifier}",
			password="password"
		)

"""
Convenience function for building a list of users.
"""
def create_users(identifiers):
	users = []
	for identifier in identifiers:
		users.append(build_user(identifier))
	return users