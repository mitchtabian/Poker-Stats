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

ci test
## Next time
1. Add CI that runs unit tests before merging.
1. Eliminations summary (who elim'd who)
1. Analytics for user
	1. Accessible from profile
	1. Shows summary across games
		- Make which tournaments you want to get summary for selectable. Like if I've been in 10 but only want summary of 8.
1. TournamentGroup? Think this through with some diagrams
1. Analaytics based on TournamentGroup
	- Basically this would just extend the per-user analytics
1. Are you sure you want to remove?
1. Make new database diagrams using that thing aaron showed you.
1. "Guest" feature.
	- If someone wanted to track their analytics and the people they were playing with do not use the site.

## TODO (after app is fully functional)
1. Optimize everything for mobile. 
	- 99% of the time this is going to be used from a phone.
1. Remove CDNs
1. Add recaptcha to registration/login https://pypi.org/project/django-recaptcha/
	- Or maybe just delete accounts after X days if they have not be verified?
1. UNIT TESTS!!!
1. Screenshot tests?
1. Figure out how to make the website timezone aware
	- Probably just need to save the timezone of the user in their profile data and then do a conversion in every view that uses a date.
1. Make admin not automatically join a tournament when they create it.
1. Add splitting feature

# Resources
1. django-allauth
	1. doc: https://django-allauth.readthedocs.io/en/latest/index.html
	1. https://github.com/ksarthak4ever/Django-Video_Subscription_App
	1. https://www.codesnail.com/django-allauth-email-authentication-tutorial
	1. https://medium.com/@ksarthak4ever/django-custom-user-model-allauth-for-oauth-20c84888c318
1. django-bootstrap-v5
	1. doc: https://django-bootstrap-v5.readthedocs.io/en/latest/index.html






