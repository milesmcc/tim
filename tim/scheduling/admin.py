from django.contrib import admin
from django.shortcuts import redirect

from . import models, tasks


class EventAdmin(admin.ModelAdmin):
    change_form_template = "scheduling/admin/event_change_form.html"
    list_display = [
        "created",
        "schedule",
        "scheduled",
        "content",
        "inception",
        "deadline",
        "duration",
        "completed",
        "source",
        "recurrence_id",
        "progression",
        "progression_order",
    ]
    list_display_links = ["created"]
    search_fields = ["content", "progression", "contexts", "flags"]
    list_filter = ["completed", "scheduled", "source", "deadline"]

    def response_change(self, request, obj):
        if "_reschedule" in request.POST:
            obj.scheduled = None
            obj.save()
            self.message_user(request, "This event has been rescheduled.")
            return redirect(".")
        return super().response_change(request, obj)


admin.site.register(models.Event, EventAdmin)


def update_schedules(modeladmin, request, queryset):
    for schedule in queryset:
        tasks.update_schedule.delay(schedule.pk)


update_schedules.short_description = "Update & process schedules"


class ScheduleAdmin(admin.ModelAdmin):
    change_form_template = "scheduling/admin/schedule_change_form.html"
    actions = [update_schedules]
    list_display = ["pk", "user", "rescheduling_behavior", "default_timezone"]
    list_display_links = ["pk"]
    search_fields = ["rescheduling_behavior", "default_timezone"]
    list_filter = ["rescheduling_behavior"]

    def response_change(self, request, obj):
        if "_update" in request.POST:
            tasks.update_schedule.delay(obj.pk)
            self.message_user(
                request, "This schedule will be recalculated in the background."
            )
            return redirect(".")
        return super().response_change(request, obj)


admin.site.register(models.Schedule, ScheduleAdmin)
