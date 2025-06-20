# Generated by Django 4.2.7 on 2025-06-11 11:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_recipe_short_link_alter_recipe_cooking_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='short_link',
            field=models.CharField(blank=True, default='', editable=False, max_length=10, unique=True, verbose_name='Короткая ссылка'),
        ),
        migrations.AlterField(
            model_name='recipeingredient',
            name='amount',
            field=models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(100)], verbose_name='Количество'),
        ),
    ]
