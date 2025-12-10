from django import forms
from .models import Record, VendorItem, Vendor, AdvanceSalary

class RecordForm(forms.ModelForm):
    LOCATION_CHOICES = [
        ('Dulari', 'Dulari'),
        ('Pours and Plates', 'Pours and Plates'),
        ('Rachels', 'Rachels'),
        ('Rachels1', 'Rachels1'),
        ('Rachels2', 'Rachels2')
    ]

    location = forms.ChoiceField(choices=LOCATION_CHOICES)

    class Meta:
        model = Record
        fields = ["date", "location", "vendor", "item", "quantity"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["item"].queryset = VendorItem.objects.none()

        if "vendor" in self.data:
            try:
                vendor_id = int(self.data.get("vendor"))
                self.fields["item"].queryset = VendorItem.objects.filter(vendor_id=vendor_id)
            except:
                pass
        elif self.instance.pk and self.instance.vendor:
            self.fields["item"].queryset = self.instance.vendor.items.all()

class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name"]

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