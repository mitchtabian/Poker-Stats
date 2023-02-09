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
1. TEST THE TOURNAMENTPLAYERRESULT stuff
	1. Try all different configurations and make sure the result data is correct
		1. rebuys
		1. no rebuys
		1. bounty
		1. no bounty
		- PROBABLY WORTH WRITING UNIT TESTS NOW!!!! Testing this manually will be very slow
	1. Go back and remove comments and prints

1. tournament_players_completed_state.html
	1. At this point the tournament is complete so lets build some graphs and summarize the data niceley. Maybe start with tables to get something working but then start thinking about graphs
	1. Eliminations summary (who elim'd who)
	1. TODO
		1. Don't allow admin to complete the tournament before every player except 1 is eliminated
		1. Future: Need a mechanism for splitting. 
1. Are you sure you want to remove?
1. Show warning modal on:
	1. activate: This will delete any pending invites
	1. complete: Tournament cannot be updated once completed.
1. Make sure there are no views you can manually visit by entering the url that you shouldn't be able to (tournament stuff depening on TournamentState)
1. Make new database diagrams using that thing aaron showed you.


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






