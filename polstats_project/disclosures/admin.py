from django.contrib import admin
from .models import (
    DisclosureReport, Contribution, Expenditure, EntityRegistration, EntityOfficer,
    LobbyistReport, LobbyistExpenditure, LobbyistRegistration, LobbyistPrincipal
)


@admin.register(DisclosureReport)
class DisclosureReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_id',
        'organization_name',
        'organization_type',
        'report_type',
        'ending_balance',
        'submit_date'
    ]
    list_filter = [
        'organization_type',
        'report_type',
        'created_at',
        'last_scraped_at',
        'submit_date'
    ]
    search_fields = [
        'report_id',
        'title',
        'organization_name',
        'organization_type'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_scraped_at']
    fieldsets = (
        ('Report Information', {
            'fields': ('report_id', 'source_url', 'title')
        }),
        ('Organization', {
            'fields': ('organization_name', 'organization_type')
        }),
        ('Report Period', {
            'fields': ('report_type', 'begin_date', 'end_date', 'due_date', 'submit_date')
        }),
        ('Financial Summary', {
            'fields': ('balance_beginning', 'total_contributions', 'total_expenditures', 'ending_balance')
        }),
        ('Metadata', {
            'fields': ('report_info', 'created_at', 'updated_at', 'last_scraped_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = [
        'contributor_name',
        'amount',
        'date_received',
        'report',
        'is_in_kind',
        'is_loan'
    ]
    list_filter = [
        'date_received',
        'is_in_kind',
        'is_loan',
        'is_amendment',
        'report'
    ]
    search_fields = ['contributor_name', 'address']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['report']


@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_name',
        'amount',
        'date',
        'purpose',
        'report',
        'is_in_kind',
        'is_loan'
    ]
    list_filter = [
        'date',
        'is_in_kind',
        'is_loan',
        'is_amendment',
        'report'
    ]
    search_fields = ['recipient_name', 'purpose']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['report']


class EntityOfficerInline(admin.TabularInline):
    model = EntityOfficer
    extra = 0
    fields = ['name', 'title', 'phone', 'email', 'is_treasurer']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EntityRegistration)
class EntityRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'entity_id',
        'name',
        'date_created',
        'city',
        'state',
        'last_scraped_at'
    ]
    list_filter = [
        'state',
        'entity_type',
        'date_created',
        'last_scraped_at'
    ]
    search_fields = [
        'entity_id',
        'name',
        'also_known_as',
        'city'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_scraped_at']
    inlines = [EntityOfficerInline]
    fieldsets = (
        ('Entity Information', {
            'fields': ('entity_id', 'source_url', 'name', 'also_known_as', 'entity_type', 'date_created', 'status')
        }),
        ('Address', {
            'fields': ('street_address', 'suite_po_box', 'city', 'state', 'zip_code')
        }),
        ('Metadata', {
            'fields': ('raw_data', 'created_at', 'updated_at', 'last_scraped_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EntityOfficer)
class EntityOfficerAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'title',
        'entity',
        'is_treasurer',
        'phone',
        'email'
    ]
    list_filter = [
        'is_treasurer',
        'title'
    ]
    search_fields = [
        'name',
        'title',
        'email',
        'entity__name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['entity']


# ============================================================================
# Lobbyist Admin
# ============================================================================


@admin.register(LobbyistReport)
class LobbyistReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_id',
        'principal_name',
        'report_type',
        'total_expenditures',
        'submit_date'
    ]
    list_filter = [
        'report_type',
        'created_at',
        'last_scraped_at',
        'submit_date'
    ]
    search_fields = [
        'report_id',
        'title',
        'principal_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_scraped_at']
    fieldsets = (
        ('Report Information', {
            'fields': ('report_id', 'source_url', 'title')
        }),
        ('Principal', {
            'fields': ('principal_name', 'principal_phone', 'principal_street_address',
                      'principal_city', 'principal_state', 'principal_zip')
        }),
        ('Report Period', {
            'fields': ('report_type', 'begin_date', 'end_date', 'due_date', 'submit_date')
        }),
        ('Financial Summary', {
            'fields': ('total_expenditures',)
        }),
        ('Metadata', {
            'fields': ('report_info', 'created_at', 'updated_at', 'last_scraped_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LobbyistExpenditure)
class LobbyistExpenditureAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_name',
        'amount',
        'date',
        'location',
        'purpose',
        'report'
    ]
    list_filter = [
        'date',
        'is_amendment',
        'report'
    ]
    search_fields = ['recipient_name', 'location', 'purpose']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['report']


class LobbyistPrincipalInline(admin.TabularInline):
    model = LobbyistPrincipal
    extra = 0
    fields = ['name', 'contact', 'phone', 'address']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LobbyistRegistration)
class LobbyistRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'entity_id',
        'name',
        'organization_name',
        'registration_date',
        'city',
        'state',
        'last_scraped_at'
    ]
    list_filter = [
        'state',
        'registration_date',
        'last_scraped_at'
    ]
    search_fields = [
        'entity_id',
        'name',
        'first_name',
        'last_name',
        'organization_name',
        'principal_name',
        'city'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_scraped_at']
    inlines = [LobbyistPrincipalInline]
    fieldsets = (
        ('Lobbyist Information', {
            'fields': ('entity_id', 'source_url', 'first_name', 'last_name', 'name',
                      'phone', 'registration_date')
        }),
        ('Organization', {
            'fields': ('organization_name', 'organization_phone')
        }),
        ('Address', {
            'fields': ('street_address', 'city', 'state', 'zip_code')
        }),
        ('Principal/Client', {
            'fields': ('principal_name', 'principal_phone', 'principal_address', 'lobbying_purposes')
        }),
        ('Metadata', {
            'fields': ('raw_data', 'created_at', 'updated_at', 'last_scraped_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LobbyistPrincipal)
class LobbyistPrincipalAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'lobbyist',
        'contact',
        'phone'
    ]
    search_fields = [
        'name',
        'contact',
        'phone',
        'lobbyist__name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['lobbyist']
