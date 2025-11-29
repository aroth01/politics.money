# Generated migration for performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disclosures', '0003_lobbyistregistration_lobbyistprincipal_and_more'),
    ]

    operations = [
        # Contribution indexes for common aggregation queries
        migrations.AddIndex(
            model_name='contribution',
            index=models.Index(
                fields=['contributor_name', 'amount'],
                name='contrib_name_amt_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='contribution',
            index=models.Index(
                fields=['address', 'amount'],
                name='contrib_addr_amt_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='contribution',
            index=models.Index(
                fields=['date_received', 'amount'],
                name='contrib_date_amt_idx'
            ),
        ),

        # Expenditure indexes for common aggregation queries
        migrations.AddIndex(
            model_name='expenditure',
            index=models.Index(
                fields=['recipient_name', 'amount'],
                name='exp_recip_amt_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='expenditure',
            index=models.Index(
                fields=['date', 'amount'],
                name='exp_date_amt_idx'
            ),
        ),

        # Report indexes for filtering
        migrations.AddIndex(
            model_name='disclosurereport',
            index=models.Index(
                fields=['end_date', 'organization_type'],
                name='report_end_orgtype_idx'
            ),
        ),
    ]
