# payroll/admin.py
from django.contrib import admin
from .models import AdvanceSalary

@admin.register(AdvanceSalary)
class AdvanceSalaryAdmin(admin.ModelAdmin):
    list_display = ("employee_name", "amount", "paid_on")
    search_fields = ("employee_name",)
    list_filter = ("paid_on",)
