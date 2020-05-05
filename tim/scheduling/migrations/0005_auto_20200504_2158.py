# Generated by Django 3.0.6 on 2020-05-04 21:58

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0004_auto_20200504_2135"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event", name="duration", field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="event",
            name="uuid",
            field=models.UUIDField(
                default=uuid.UUID("6d7578ed-5061-481a-8f79-15c3218bcdc7"),
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
