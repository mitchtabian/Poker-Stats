error_unsuccessful_registration = "Unsuccessful registration. Invalid information."
invalid_email_or_password = "Invalid email or password."
password_is_incorrect = "Password is incorrect."
passwords_dont_match_error = "Passwords don't match."
registration_successful = "Registration successful. Check your email to login."

def login_success(user):
	return f"Login success! You are now logged in as {user}."

def user_with_email_does_not_exist(email):
	return f'A user with email={email} does not exist.'
