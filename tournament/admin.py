from django.contrib import admin

from .models import TournamentStructure, Tournament, TournamentPlayer, TournamentElimination, TournamentInvite, TournamentPlayerResult


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
        (None, {'fields': ('user', 'tournament', 'num_rebuys')}),
    )

    list_display = ('user', 'tournament', 'num_rebuys')
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
        (None, {'fields': ('tournament', 'eliminator', 'eliminatee', 'eliminated_at')}),
    )

    list_display = ('tournament', 'eliminator', 'eliminatee', 'eliminated_at')
    search_fields = ('tournament', 'eliminator', 'eliminatee', )


admin.site.register(TournamentElimination, TournamentEliminationAdmin)

class TournamentPlayerResultAdmin(admin.ModelAdmin):

    fieldsets = (
        (None, {'fields': ('player', 'tournament', 'net_earnings', 'gross_earnings')}),
    )

    list_display = ('player', 'tournament', 'net_earnings',  'gross_earnings', 'elimination_ids')
    search_fields = ('player', 'tournament',)


admin.site.register(TournamentPlayerResult, TournamentPlayerResultAdmin)










