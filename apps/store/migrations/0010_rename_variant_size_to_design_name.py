from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0009_product_meta_description_product_meta_title_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productvariant',
            name='unique_product_color_size',
        ),

        migrations.RenameField(
            model_name='productvariant',
            old_name='size',
            new_name='design_name',
        ),

        migrations.AlterField(
            model_name='productvariant',
            name='design_name',
            field=models.CharField(
                blank=True,
                max_length=50,
                verbose_name='نام طرح',
            ),
        ),

        migrations.AlterModelOptions(
            name='productvariant',
            options={
                'ordering': [
                    'color_name',
                    'design_name',
                ],
                'verbose_name': 'تنوع محصول',
                'verbose_name_plural': 'تنوع‌های محصول',
            },
        ),

        migrations.AddConstraint(
            model_name='productvariant',
            constraint=models.UniqueConstraint(
                fields=(
                    'product',
                    'color_name',
                    'design_name',
                ),
                name='unique_product_color_design',
            ),
        ),
    ]
