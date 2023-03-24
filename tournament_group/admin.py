from django.contrib import admin

from tournament_group.models import TournamentGroup

class TournamentGroupAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('admin', 'title', 'get_tournament_count', 'get_user_count', 'start_at', 'end_at')}),
    )
    readonly_fields = ['get_tournament_count', 'get_user_count']

    list_display = ('admin', 'title', 'get_tournament_count', 'get_user_count', 'start_at', 'end_at')
    search_fields = ('admin', 'title')

    @admin.display(description='Tournament Count')
    def get_tournament_count(self, tournament_group):
        return len(tournament_group.get_tournaments())

    @admin.display(description='User Count')
    def get_user_count(self, tournament_group):
        return len(tournament_group.get_users())

admin.site.register(TournamentGroup, TournamentGroupAdmin)
