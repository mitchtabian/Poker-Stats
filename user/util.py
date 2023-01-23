import re

email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Validate an email address.
def validate_email(email):
	if(re.fullmatch(email_regex, email)):
		return email
	else:
		raise ValueError(f'{email} is not a valid email address.')

