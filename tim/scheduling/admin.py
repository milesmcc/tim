from django.contrib import admin

from . import models, tasks


class EventAdmin(admin.ModelAdmin):
    list_display = [
        "schedule",
        "created",
        "scheduled",
        "content",
        "inception",
        "deadline",
        "duration",
        "completed",
        "source",
        "recurrence_id"
    ]
    search_fields = ["schedule", "schedule.user", "content", "contexts", "flags"]
    list_filter = ["completed", "scheduled"]


admin.site.register(models.Event, EventAdmin)


def update_schedules(modeladmin, request, queryset):
    for schedule in queryset:
        tasks.update_schedule.delay(schedule.pk)


update_schedules.short_description = "Update & process schedules"


class ScheduleAdmin(admin.ModelAdmin):
    actions = [update_schedules]
    list_display = ["pk", "user", "rescheduling_behavior", "default_timezone"]
    list_display_links = ["pk"]
    search_fields = ["user", "rescheduling_behavior", "default_timezone"]
    list_filter = ["rescheduling_behavior"]


admin.site.register(models.Schedule, ScheduleAdmin)
