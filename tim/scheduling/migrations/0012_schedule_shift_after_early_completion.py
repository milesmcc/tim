# Generated by Django 3.0.6 on 2020-05-07 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0011_auto_20200507_1053'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='shift_after_early_completion',
            field=models.BooleanField(default=True),
        ),
    ]