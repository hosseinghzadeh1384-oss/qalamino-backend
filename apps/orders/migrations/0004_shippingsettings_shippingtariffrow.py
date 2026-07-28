from django.db import migrations, models


DEFAULT_TARIFF_ROWS = [
    # (سقف وزن گرم, هزینه تهران, هزینه سایر استان‌ها) - همان مقادیرِ قبلیِ settings.PISHTAZ_POST_TARIFF
    (500, 45_000, 55_000),
    (1_000, 60_000, 75_000),
    (2_000, 80_000, 100_000),
    (5_000, 120_000, 150_000),
    (10_000, 180_000, 230_000),
    (20_000, 280_000, 350_000),
]

DEFAULT_EXTRA_COST_PER_KG = 20_000


def seed_default_data(apps, schema_editor):
    ShippingSettings = apps.get_model('orders', 'ShippingSettings')
    ShippingTariffRow = apps.get_model('orders', 'ShippingTariffRow')

    ShippingSettings.objects.get_or_create(
        pk=1,
        defaults={'extra_cost_per_kg': DEFAULT_EXTRA_COST_PER_KG},
    )

    for max_weight_grams, tehran_price, other_price in DEFAULT_TARIFF_ROWS:
        ShippingTariffRow.objects.get_or_create(
            max_weight_grams=max_weight_grams,
            defaults={'tehran_price': tehran_price, 'other_price': other_price},
        )


def remove_seeded_data(apps, schema_editor):
    ShippingSettings = apps.get_model('orders', 'ShippingSettings')
    ShippingTariffRow = apps.get_model('orders', 'ShippingTariffRow')
    ShippingSettings.objects.filter(pk=1).delete()
    ShippingTariffRow.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_orderitem_variant_orderitem_variant_label'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShippingSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'extra_cost_per_kg',
                    models.PositiveIntegerField(
                        default=20_000,
                        help_text=(
                            'اگر وزن مرسوله از بیشترین سقفِ جدول تعرفه بالاتر برود، به ازای هر ۱ کیلوگرم اضافه '
                            '(یا کسری از آن) این مقدار روی هزینه‌ی آخرین ردیف جدول افزوده می‌شود.'
                        ),
                        verbose_name='هزینه اضافه به ازای هر کیلوگرم مازاد (تومان)',
                    ),
                ),
            ],
            options={
                'verbose_name': 'تنظیمات هزینه ارسال',
                'verbose_name_plural': 'تنظیمات هزینه ارسال',
            },
        ),
        migrations.CreateModel(
            name='ShippingTariffRow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_weight_grams', models.PositiveIntegerField(unique=True, verbose_name='سقف وزن (گرم)')),
                ('tehran_price', models.PositiveIntegerField(verbose_name='هزینه برای تهران (تومان)')),
                ('other_price', models.PositiveIntegerField(verbose_name='هزینه برای سایر استان\u200cها (تومان)')),
            ],
            options={
                'verbose_name': 'ردیف تعرفه پست پیشتاز',
                'verbose_name_plural': 'جدول تعرفه پست پیشتاز',
                'ordering': ['max_weight_grams'],
            },
        ),
        migrations.RunPython(seed_default_data, remove_seeded_data),
    ]
