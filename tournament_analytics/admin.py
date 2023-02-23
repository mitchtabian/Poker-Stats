from django.contrib import admin

from tournament_analytics.models import TournamentTotals

class TournamentTotalsAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('user', 'rebuild_hash', 'tournaments_played', 'gross_earnings', 'net_earnings', 'losses', 'eliminations', 'rebuys', 'timestamp')}),
    )
    readonly_fields = ['user', 'rebuild_hash', 'tournaments_played', 'gross_earnings', 'net_earnings', 'losses', 'eliminations', 'rebuys', 'timestamp']

    list_display = ('user', 'tournaments_played', 'timestamp')
    search_fields = ('user', 'timestamp')


admin.site.register(TournamentTotals, TournamentTotalsAdmin)
