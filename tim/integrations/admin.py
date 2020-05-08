from django.contrib import admin

from . import models

class IntegrationFilter(admin.ModelAdmin):
    list_display = ["pk", "schedule", "service"]
    list_filter = ["service"]

admin.site.register(models.Integration, IntegrationFilter)
