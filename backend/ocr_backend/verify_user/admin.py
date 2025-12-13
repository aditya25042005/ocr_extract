from django.contrib import admin
from .models import PassportRecord

@admin.register(PassportRecord)
class PassportRecordAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "dob",
        "gender",
        "present_city",
        "created_at",
    )

    search_fields = (
        "first_name",
        "last_name",
        "present_city",
        "passport_number",
    )

    list_filter = ("gender", "present_state", "created_at")
