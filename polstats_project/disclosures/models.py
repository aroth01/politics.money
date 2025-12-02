from django.db import models
from django.utils import timezone


class DisclosureReport(models.Model):
    """Main disclosure report record."""

    report_id = models.CharField(max_length=50, unique=True, db_index=True)
    source_url = models.URLField(max_length=500)
    title = models.CharField(max_length=500, blank=True)

    # Organization information
    organization_name = models.CharField(max_length=500, blank=True, db_index=True)
    organization_type = models.CharField(max_length=100, blank=True, db_index=True)
    # Types: Political Party, Political Action Committee, Candidate, etc.

    # Report period information
    report_type = models.CharField(max_length=200, blank=True)
    begin_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    submit_date = models.DateField(null=True, blank=True)

    # Balance summary fields
    balance_beginning = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_contributions = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_expenditures = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ending_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Additional metadata
    report_info = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scraped_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['report_id']),
            models.Index(fields=['organization_type']),
            models.Index(fields=['organization_name']),
        ]

    def __str__(self):
        return f"Report {self.report_id} - {self.organization_name or self.title}"


class Contribution(models.Model):
    """Individual contribution record."""

    report = models.ForeignKey(
        DisclosureReport,
        on_delete=models.CASCADE,
        related_name='contributions'
    )

    date_received = models.DateField(null=True, blank=True)
    date_received_raw = models.CharField(max_length=50, blank=True)

    contributor_name = models.CharField(max_length=500)
    address = models.TextField(blank=True)

    # Flags
    is_in_kind = models.BooleanField(default=False)
    is_loan = models.BooleanField(default=False)
    is_amendment = models.BooleanField(default=False)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_received', '-created_at']
        indexes = [
            models.Index(fields=['report', '-date_received']),
            models.Index(fields=['contributor_name']),
            models.Index(fields=['-amount']),
        ]

    def __str__(self):
        return f"{self.contributor_name} - ${self.amount} on {self.date_received}"


class Expenditure(models.Model):
    """Individual expenditure record."""

    report = models.ForeignKey(
        DisclosureReport,
        on_delete=models.CASCADE,
        related_name='expenditures'
    )

    date = models.DateField(null=True, blank=True)
    date_raw = models.CharField(max_length=50, blank=True)

    recipient_name = models.CharField(max_length=500)
    address = models.TextField(blank=True)  # Location/venue for lobbyist expenditures
    purpose = models.TextField(blank=True)

    # Flags
    is_in_kind = models.BooleanField(default=False)
    is_loan = models.BooleanField(default=False)
    is_amendment = models.BooleanField(default=False)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['report', '-date']),
            models.Index(fields=['recipient_name']),
            models.Index(fields=['-amount']),
        ]

    def __str__(self):
        return f"{self.recipient_name} - ${self.amount} on {self.date}"


class EntityRegistration(models.Model):
    """Political entity registration information."""

    entity_id = models.CharField(max_length=50, unique=True, db_index=True)
    source_url = models.URLField(max_length=500)

    # Entity information
    name = models.CharField(max_length=500, db_index=True)
    also_known_as = models.CharField(max_length=500, blank=True)
    entity_type = models.CharField(max_length=100, blank=True)
    date_created = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True)

    # Primary address
    street_address = models.CharField(max_length=500, blank=True)
    suite_po_box = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # Additional data stored as JSON
    raw_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scraped_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} (ID: {self.entity_id})"


class EntityOfficer(models.Model):
    """Officers/committee members for political entities."""

    entity = models.ForeignKey(
        EntityRegistration,
        on_delete=models.CASCADE,
        related_name='officers'
    )

    # Officer information
    name = models.CharField(max_length=500)
    title = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=200, blank=True)

    # Contact information
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)

    # Address
    street_address = models.CharField(max_length=500, blank=True)
    suite_po_box = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # Order and role
    order = models.IntegerField(default=0)
    is_treasurer = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['entity', 'order']

    def __str__(self):
        return f"{self.name} - {self.title} ({self.entity.name})"


# ============================================================================
# Lobbyist Models
# ============================================================================


class LobbyistReport(models.Model):
    """Lobbyist expenditure report record."""

    report_id = models.CharField(max_length=50, unique=True, db_index=True)
    source_url = models.URLField(max_length=500)
    title = models.CharField(max_length=500, blank=True)

    # Principal/Organization information
    principal_name = models.CharField(max_length=500, blank=True, db_index=True)
    principal_phone = models.CharField(max_length=50, blank=True)
    principal_street_address = models.CharField(max_length=500, blank=True)
    principal_city = models.CharField(max_length=200, blank=True)
    principal_state = models.CharField(max_length=2, blank=True)
    principal_zip = models.CharField(max_length=10, blank=True)

    # Report period information
    report_type = models.CharField(max_length=200, blank=True)
    begin_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    submit_date = models.DateField(null=True, blank=True)

    # Balance summary
    total_expenditures = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Additional metadata
    report_info = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scraped_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['report_id']),
            models.Index(fields=['principal_name']),
        ]

    def __str__(self):
        return f"Lobbyist Report {self.report_id} - {self.principal_name or self.title}"


class LobbyistExpenditure(models.Model):
    """Individual lobbyist expenditure record."""

    report = models.ForeignKey(
        LobbyistReport,
        on_delete=models.CASCADE,
        related_name='expenditures'
    )

    date = models.DateField(null=True, blank=True)
    date_raw = models.CharField(max_length=50, blank=True)

    recipient_name = models.CharField(max_length=500, db_index=True)
    location = models.CharField(max_length=500, blank=True)
    purpose = models.TextField(blank=True)

    # Flags
    is_amendment = models.BooleanField(default=False)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['report', '-date']),
            models.Index(fields=['recipient_name']),
            models.Index(fields=['-amount']),
        ]

    def __str__(self):
        return f"{self.recipient_name} - ${self.amount} on {self.date}"


class LobbyistRegistration(models.Model):
    """Lobbyist entity registration information."""

    entity_id = models.CharField(max_length=50, unique=True, db_index=True)
    source_url = models.URLField(max_length=500)

    # Lobbyist personal information
    first_name = models.CharField(max_length=200, blank=True)
    last_name = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=500, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    registration_date = models.DateField(null=True, blank=True)

    # Business/Organization information
    organization_name = models.CharField(max_length=500, blank=True)
    organization_phone = models.CharField(max_length=50, blank=True)
    street_address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # Principal/Client information
    principal_name = models.CharField(max_length=500, blank=True)
    principal_phone = models.CharField(max_length=50, blank=True)
    principal_address = models.TextField(blank=True)
    lobbying_purposes = models.TextField(blank=True)

    # Additional data stored as JSON
    raw_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scraped_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_id']),
            models.Index(fields=['name']),
            models.Index(fields=['organization_name']),
        ]

    def __str__(self):
        return f"{self.name} (ID: {self.entity_id})"


class LobbyistPrincipal(models.Model):
    """Principal/Client organizations for lobbyists."""

    lobbyist = models.ForeignKey(
        LobbyistRegistration,
        on_delete=models.CASCADE,
        related_name='principals'
    )

    # Principal information
    name = models.CharField(max_length=500)
    contact = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    # Order
    order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['lobbyist', 'order']

    def __str__(self):
        return f"{self.name} (Principal for {self.lobbyist.name})"
