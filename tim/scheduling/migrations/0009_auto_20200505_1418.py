# Generated by Django 3.0.6 on 2020-05-05 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0008_schedule_reschedule_after"),
    ]

    operations = [
        migrations.AlterField(
            model_name="schedule",
            name="reschedule_after",
            field=models.IntegerField(default=1800),
        ),
    ]
