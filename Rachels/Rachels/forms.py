from django import forms
from .models import *
from datetime import date

class RecordForm(forms.ModelForm):

    class Meta:
        model = Record
        fields = ["date", "location"]
        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
            "location": forms.Select(attrs={
                "class": "form-control"
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = date.today()

        # ✅ Date: auto-set & locked to today
        self.fields["date"].initial = today
        self.fields["date"].widget.attrs.update({
            "min": today,
            "max": today,
            "readonly": True
        })

        # ✅ Location: only active stores from DB
        self.fields["location"].queryset = Store.objects.filter(is_active=True)

    def clean_date(self):
        selected_date = self.cleaned_data.get("date")
        today = date.today()

        # ✅ HARD backend validation (cannot be bypassed)
        if selected_date != today:
            raise forms.ValidationError("Date must be today's date.")

        return selected_date
class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Vendor name"
            })
        }

class AdvanceSalaryForm(forms.ModelForm):
    class Meta:
        model = AdvanceSalary
        fields = ["employee_name", "paid_on", "amount"]
        widgets = {
            "paid_on": forms.DateInput(attrs={"type": "date", "id": "id_paid_on"}),
            "employee_name": forms.TextInput(attrs={"placeholder": "Employee name", "id": "id_employee_name"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0", "id": "id_amount"}),
        }

    def clean_amount(self):
        a = self.cleaned_data.get("amount")
        if a is None or a <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return a
    
class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ["name", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter store name"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            })
        }