class EmailAlreadyInUseException(Exception):
	"""
	Exception raised when an email is already in use.

	Attributes:
	email -- The email that is already in use.
	message -- explanation of the error
	"""

	def __init__(self, email):
		self.email = email
		self.message = f"The email {email} is already in use."
		super().__init__(self.message)
