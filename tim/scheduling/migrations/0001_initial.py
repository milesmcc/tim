# Generated by Django 3.0.5 on 2020-05-04 14:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Schedule",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "rescheduling_behavior",
                    models.TextField(
                        choices=[
                            ("CONSISTENCY", "Optimize for consistency"),
                            ("EFFICIENCY", "Optimize for efficiency"),
                        ],
                        default="EFFICIENCY",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                ("uuid", models.UUIDField(primary_key=True, serialize=False)),
                ("inception", models.DateTimeField(null=True)),
                ("scheduled", models.DateTimeField(null=True)),
                ("deadline", models.DateTimeField(null=True)),
                ("duration", models.IntegerField(default=30)),
                ("completed", models.BooleanField(default=False)),
                ("flags", models.TextField(blank=True)),
                ("contexts", models.TextField(blank=True)),
                ("source", models.TextField()),
                ("source_id", models.TextField(db_index=True)),
                ("source_url", models.URLField(blank=True)),
                ("recurrence_id", models.TextField(blank=True)),
                (
                    "schedule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="scheduling.Schedule",
                    ),
                ),
            ],
        ),
    ]
