from django import forms
from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Nome',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Cognome',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Email',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Telefono',
            }),
            'address': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Indirizzo',
            }),
            'role': forms.Select(attrs={
                'class': 'select select-bordered w-full',
            }),
        }
        labels = {
            'first_name': 'Nome',
            'last_name': 'Cognome',
            'email': 'Email',
            'phone_number': 'Telefono',
            'address': 'Indirizzo',
            'role': 'Ruolo',
        }
