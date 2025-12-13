# Generated manually to add address field to Expenditure model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disclosures', '0005_remove_contribution_contrib_name_amt_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenditure',
            name='address',
            field=models.TextField(blank=True),
        ),
    ]
