from django.contrib import admin
from account.models import Account

class AccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'date_joined', 'last_login', 'is_admin', 'is_staff']
    readonly_fields = ['id', 'date_joined', 'password', 'last_login',]
    search_fields = ['email', 'username']

    class Meta:
        model = Account

admin.site.register(Account, AccountAdmin)
