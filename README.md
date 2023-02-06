Project for tracking poker stats from tournaments. 

**This is a work in progress**.

# Features:
1. User management
	1. Registration
	1. Login
	1. Password reset
	1. Email/account verification
	1. Google account signup
1. Track game statistics
1. Personalized game statistics
1. TODO... more stuff


# TODO
This is a notes section for me personally.

## Next time
1. tournament structure UI
	- This is fucked. Using a form seems impossible since I have to dynamically add "positions". 
	- Maybe I can render the "first place" integer field only, and then render additional ones using ajax. Then in the form.save method I can find those fields and set them. That seems like it would work.
	- https://www.caktusgroup.com/blog/2018/05/07/creating-dynamic-forms-django/
1. Unit test tournament stuff


## TODO (after app is fully functional)
1. Messages UI
1. Add recaptcha to registration/login https://pypi.org/project/django-recaptcha/
	- Or maybe just delete accounts after X days if they have not be verified?
1. Improve UI. It looks like shit


# Resources
1. django-allauth
	1. doc: https://django-allauth.readthedocs.io/en/latest/index.html
	1. https://github.com/ksarthak4ever/Django-Video_Subscription_App
	1. https://www.codesnail.com/django-allauth-email-authentication-tutorial
	1. https://medium.com/@ksarthak4ever/django-custom-user-model-allauth-for-oauth-20c84888c318
1. django-bootstrap-v5
	1. doc: https://django-bootstrap-v5.readthedocs.io/en/latest/index.html

