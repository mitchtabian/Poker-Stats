from django.contrib import admin

from .models import TournamentStructure, Tournament, TournamentPlayer, TournamentElimination, TournamentInvite, TournamentPlayerResult, TournamentRebuy


class TournamentStructureAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'user', 'buyin_amount', 'bounty_amount', 'payout_percentages', 'allow_rebuys')}),
    )

    list_display = ('pk', 'title', 'user', 'buyin_amount')
    search_fields = ('title', 'user')


admin.site.register(TournamentStructure, TournamentStructureAdmin)


class TournamentAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'admin', 'tournament_structure', 'started_at', 'completed_at')}),
    )

    list_display = ('title', 'admin', 'tournament_structure')
    search_fields = ('title', 'admin')


admin.site.register(Tournament, TournamentAdmin)


class TournamentPlayerAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('user', 'tournament')}),
    )

    list_display = ('user', 'id', 'tournament')
    search_fields = ('user', 'tournament')


admin.site.register(TournamentPlayer, TournamentPlayerAdmin)

class TournamentInviteAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('send_to', 'tournament')}),
    )

    list_display = ('send_to', 'tournament')
    search_fields = ('send_to', 'tournament' )


admin.site.register(TournamentInvite, TournamentInviteAdmin)

class TournamentEliminationAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('get_tournament_title', 'eliminator', 'eliminatee', 'eliminated_at')}),
    )
    readonly_fields = ['eliminated_at', 'get_tournament_title', 'eliminator', 'eliminatee',]
    list_display = ('get_tournament', 'eliminator', 'eliminatee', 'eliminated_at')
    search_fields = ('get_tournament', 'eliminator', 'eliminatee', )

    @admin.display(description='Tournament')
    def get_tournament(self, elimination):
        return elimination.get_tournament_title()

admin.site.register(TournamentElimination, TournamentEliminationAdmin)

class TournamentRebuyAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('get_tournament', 'get_player_username','timestamp')}),
    )
    readonly_fields = ['get_tournament', 'get_player_username', 'timestamp']

    list_display = ('get_tournament', 'get_player_username', 'timestamp')
    search_fields = ('get_tournament', 'get_player_username')

    @admin.display(description='Tournament')
    def get_tournament(self, rebuy):
        return rebuy.get_tournament_title()

    @admin.display(description='Username')
    def get_username(self, rebuy):
        return rebuy.get_player_username()


admin.site.register(TournamentRebuy, TournamentRebuyAdmin)

class TournamentPlayerResultAdmin(admin.ModelAdmin):

    fieldsets = (
        (None, {'fields': ('player', 'tournament', 'net_earnings', 'gross_earnings', 'placement')}),
    )

    list_display = ('player', 'tournament', 'net_earnings', 'placement', 'gross_earnings')
    search_fields = ('player', 'tournament',)


admin.site.register(TournamentPlayerResult, TournamentPlayerResultAdmin)










