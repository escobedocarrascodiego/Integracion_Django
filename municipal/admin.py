from django.contrib import admin

from municipal.models import Complaint, ComplaintEvent, Procedure, Requirement


class RequirementInline(admin.TabularInline):
    model = Requirement
    extra = 0


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "office", "fee", "processing_days", "available_online"]
    list_filter = ["office", "available_online"]
    search_fields = ["code", "name", "description"]
    inlines = [RequirementInline]


class ComplaintEventInline(admin.TabularInline):
    model = ComplaintEvent
    extra = 0


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["tracking_code", "citizen_name", "category", "status", "assigned_office", "updated_at"]
    list_filter = ["status", "category"]
    search_fields = ["tracking_code", "citizen_dni", "citizen_name"]
    date_hierarchy = "created_at"
    inlines = [ComplaintEventInline]
