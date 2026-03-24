from django.contrib import admin
from .models import Contact, DeadlineRule, Fascicolo, FascicoloParty, ProceedingType


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'role']
    list_filter = ['role']
    search_fields = ['first_name', 'last_name', 'email']


class DeadlineRuleInline(admin.TabularInline):
    model = DeadlineRule
    extra = 1
    fields = ['label', 'anchor', 'offset_days', 'reminder_days_before', 'is_active']


@admin.register(ProceedingType)
class ProceedingTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DeadlineRuleInline]


@admin.register(DeadlineRule)
class DeadlineRuleAdmin(admin.ModelAdmin):
    list_display = ['label', 'proceeding_type', 'anchor', 'offset_days', 'is_active']
    list_filter = ['proceeding_type', 'anchor', 'is_active']
    search_fields = ['label']


class FascicoloPartyInline(admin.TabularInline):
    model = FascicoloParty
    extra = 1
    fields = ['contact', 'role']
    autocomplete_fields = ['contact']


@admin.register(Fascicolo)
class FascicoloAdmin(admin.ModelAdmin):
    list_display = ['display_title', 'court', 'proceeding_type', 'status', 'opened_date', 'owner']
    list_filter = ['status', 'proceeding_type']
    search_fields = ['auto_title', 'custom_title', 'rg_number', 'court']
    readonly_fields = ['auto_title', 'created_at', 'updated_at']
    inlines = [FascicoloPartyInline]


@admin.register(FascicoloParty)
class FascicoloPartyAdmin(admin.ModelAdmin):
    list_display = ['fascicolo', 'contact', 'role']
    list_filter = ['role']
    search_fields = ['fascicolo__auto_title', 'contact__last_name']
