import apps.accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='receiver_phone',
            field=models.CharField(
                max_length=11,
                validators=[apps.accounts.models.phone_regex],
                verbose_name='تلفن گیرنده',
            ),
        ),
    ]
