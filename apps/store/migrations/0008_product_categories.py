from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_alter_brand_slug_alter_category_slug_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='categories',
            field=models.ManyToManyField(
                blank=True,
                related_name='multi_category_products',
                to='store.category',
                verbose_name='دسته‌بندی‌های بیشتر',
            ),
        ),
    ]