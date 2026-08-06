from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0007_client_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='app_pin',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
