from django.contrib import admin
from .models import Contact

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'role']
    list_filter = ['role']
    search_fields = ['first_name', 'last_name', 'email']
