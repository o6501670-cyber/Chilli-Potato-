from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('staff', '0019_servicelog_slog_center_date_staff_idx'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staffmember',
            name='app_password',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
