from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_rename_store_produ_product_9c1e21_idx_store_produ_product_b7cdb9_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='weight_grams',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='اگر خالی بماند، برای محاسبه‌ی هزینه‌ی ارسال از وزن محصول اصلی استفاده می‌شود.',
                verbose_name='وزن (گرم)',
            ),
        ),
    ]
