from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audit_logs', '0005_systemlog_syslog_module_action_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemlog',
            name='response_status',
            field=models.PositiveSmallIntegerField(default=200),
        ),
        migrations.AddField(
            model_name='systemlog',
            name='success',
            field=models.BooleanField(default=True),
        ),
    ]
