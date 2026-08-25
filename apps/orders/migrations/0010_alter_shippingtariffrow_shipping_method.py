import django.db.models.deletion
from django.db import migrations, models


def assign_default_shipping_method(apps, schema_editor):
    ShippingMethod = apps.get_model('orders', 'ShippingMethod')
    ShippingTariffRow = apps.get_model('orders', 'ShippingTariffRow')
    ShippingSettings = apps.get_model('orders', 'ShippingSettings')

    # هزینه هر کیلوگرم مازاد از تنظیمات قبلی خوانده می‌شود
    shipping_settings = ShippingSettings.objects.filter(pk=1).first()

    extra_cost_per_kg = (
        shipping_settings.extra_cost_per_kg
        if shipping_settings
        else 20_000
    )

    # روش ارسال پیش‌فرض برای تعرفه‌های قدیمی
    shipping_method, _ = ShippingMethod.objects.get_or_create(
        code='pishtaz',
        defaults={
            'name': 'پست پیشتاز',
            'description': '',
            'estimated_delivery_time': '۲ تا ۴ روز کاری',
            'extra_cost_per_kg': extra_cost_per_kg,
            'is_active': True,
            'sort_order': 0,
        },
    )

    # اتصال همه تعرفه‌های قدیمی که shipping_method ندارند
    ShippingTariffRow.objects.filter(
        shipping_method__isnull=True
    ).update(
        shipping_method=shipping_method
    )


def reverse_assign_default_shipping_method(apps, schema_editor):
    # در rollback داده‌های تعرفه را حذف یا دستکاری نمی‌کنیم
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0009_shippingmethod_alter_shippingtariffrow_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            assign_default_shipping_method,
            reverse_assign_default_shipping_method,
        ),

        migrations.AlterField(
            model_name='shippingtariffrow',
            name='shipping_method',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tariff_rows',
                to='orders.shippingmethod',
                verbose_name='روش ارسال',
            ),
        ),
    ]
