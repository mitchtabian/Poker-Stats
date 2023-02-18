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
1. CI still broken with --debug-mode?
1. Google signin issue? Not working for people to sign up with google account (See screenshot saved)
1. Setup bugsnag
1. Create a pokerstats.lol email for verifications and other stuff
1. Fix all the django-allauth templates to reference pokerstats.lol
1. Do not remove pending invites when activating tournament.
	- This will get annoying in practice. So allow tournaments to be filled out and completed without a person confirming.
	- Think about this more...?
1. Setup Jira for further feature work
1. Analytics for user
	1. Accessible from profile
	1. Shows summary across games
		- Make which tournaments you want to get summary for selectable. Like if I've been in 10 but only want summary of 8.
1. Design a landing page
	1. On mobile optimize for quickly creating or joining a tournament

1. TournamentGroup? Think this through with some diagrams
1. Analaytics based on TournamentGroup
	- Basically this would just extend the per-user analytics

## TODO (after app is fully functional)
1. Optimize everything for mobile. (I think this is already done, but confirm)
	- 99% of the time this is going to be used from a phone.
1. Remove CDNs
1. Add recaptcha to registration/login https://pypi.org/project/django-recaptcha/
	- Or maybe just delete accounts after X days if they have not be verified?
1. Screenshot tests?
1. Figure out how to make the website timezone aware
	- Probably just need to save the timezone of the user in their profile data and then do a conversion in every view that uses a date.
1. Make admin not automatically join a tournament when they create it.
1. Add splitting feature
1. Shareable invite link to a tournament? If user has no registered then they are prompted to before joining.
1. Create Jira project with an email from whatever domain I end up using.
1. "Guest" feature. Dunno if I really want this it would be very complicated. PRobably something to think about after launch.
	- If someone wanted to track their analytics and the people they were playing with do not use the site.
	- Also for backfilling, not everyone may have registered or something
	- Also need some kind of mechanism for going back into a completed Tournament and assigning a user to a guest. Like if you finished a tournament with a guest you could go back and assign a real user to it
	- Ability to give the Guest a temporary name. Just a string.

# Resources
1. django-allauth
	1. doc: https://django-allauth.readthedocs.io/en/latest/index.html
	1. https://github.com/ksarthak4ever/Django-Video_Subscription_App
	1. https://www.codesnail.com/django-allauth-email-authentication-tutorial
	1. https://medium.com/@ksarthak4ever/django-custom-user-model-allauth-for-oauth-20c84888c318
1. django-bootstrap-v5
	1. doc: https://django-bootstrap-v5.readthedocs.io/en/latest/index.html






