# Generated by Django 3.0.6 on 2020-05-05 01:24

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0006_auto_20200504_2214'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='days_of_week',
            field=models.TextField(default='Mon Tue Wed Thu Fri Sat Sun'),
        ),
        migrations.AddField(
            model_name='schedule',
            name='end_day_at',
            field=models.TimeField(default=datetime.time(22, 0)),
        ),
        migrations.AddField(
            model_name='schedule',
            name='start_day_at',
            field=models.TimeField(default=datetime.time(7, 0)),
        ),
        migrations.AlterField(
            model_name='event',
            name='deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='duration',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='inception',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='scheduled',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]