from django import forms
from .models import Record

class RecordForm(forms.ModelForm):
    LOCATION_CHOICES = [
        ('Dulari', 'Dulari'),
        ('Pours and Plates', 'Pours and Plates'),
        ('Rachels', 'Rachels'),
    ]

    location = forms.ChoiceField(choices=LOCATION_CHOICES)

    class Meta:
        model = Record
        fields = ['date', 'location', 'details']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'location': forms.TextInput(attrs={'placeholder': 'Location'}),
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Details...'}),
        }