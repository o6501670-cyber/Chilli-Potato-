from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('staff', '0016_staffmember_designation_fk_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staffmember',
            name='app_password',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
