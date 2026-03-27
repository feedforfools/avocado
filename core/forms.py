from django import forms
from .models import Activity, Contact, Fascicolo, ProceedingType


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


_INPUT = 'input input-bordered w-full'
_SELECT = 'select select-bordered w-full'
_TEXTAREA = 'textarea textarea-bordered w-full'


class FascicoloCreateForm(forms.Form):
    """Single form that creates both the Fascicolo and its initial parties.

    Party fields (client_contact, opposing_party_contact) hold Contact PKs
    scoped to the requesting user — the queryset is injected in __init__.
    The view is responsible for creating FascicoloParty records from the
    cleaned data inside a transaction.atomic() block.
    """

    # ------------------------------------------------------------------ #
    # Proceeding fields                                                    #
    # ------------------------------------------------------------------ #

    court = forms.CharField(
        label='Tribunale',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': _INPUT,
            'placeholder': 'es. Tribunale di Udine',
        }),
    )
    rg_number = forms.CharField(
        label='RG',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': _INPUT,
            'placeholder': 'es. 1234/2025',
        }),
    )
    proceeding_type = forms.ModelChoiceField(
        label='Tipo procedimento',
        queryset=ProceedingType.objects.filter(is_active=True),
        required=False,
        empty_label='— Seleziona tipo —',
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    status = forms.ChoiceField(
        label='Stato',
        choices=Fascicolo.STATUS_CHOICES,
        initial='active',
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    opened_date = forms.DateField(
        label='Data apertura',
        widget=forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
    )
    first_hearing_date = forms.DateField(
        label='Prima udienza',
        required=False,
        widget=forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}),
    )

    # ------------------------------------------------------------------ #
    # Party fields — querysets injected per-user in __init__              #
    # ------------------------------------------------------------------ #

    client_contact = forms.ModelChoiceField(
        label='Assistito',
        queryset=Contact.objects.none(),
        required=False,
        empty_label='— Seleziona assistito —',
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    opposing_party_contact = forms.ModelChoiceField(
        label='Controparte',
        queryset=Contact.objects.none(),
        required=False,
        empty_label='— Seleziona controparte —',
        widget=forms.Select(attrs={'class': _SELECT}),
    )

    # ------------------------------------------------------------------ #
    # Optional overrides                                                  #
    # ------------------------------------------------------------------ #

    custom_title = forms.CharField(
        label='Titolo personalizzato',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': _INPUT,
            'placeholder': 'Lascia vuoto per titolo automatico (es. Rossi c/ Bianchi – Trib. Udine 2025)',
        }),
    )
    notes = forms.CharField(
        label='Note interne',
        required=False,
        widget=forms.Textarea(attrs={
            'class': _TEXTAREA,
            'rows': '3',
            'placeholder': 'Note interne sul fascicolo (non visibili al cliente)',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            contacts_qs = Contact.objects.filter(owner=user).order_by('last_name', 'first_name')
            self.fields['client_contact'].queryset = contacts_qs
            self.fields['opposing_party_contact'].queryset = contacts_qs


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['date', 'activity_type', 'dm55_phase', 'duration_hours', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': _INPUT,
                'type': 'date',
            }),
            'activity_type': forms.Select(attrs={'class': _SELECT}),
            'dm55_phase': forms.Select(attrs={'class': _SELECT}),
            'duration_hours': forms.NumberInput(attrs={
                'class': _INPUT,
                'placeholder': 'es. 1.5',
                'min': '0.25',
                'step': '0.25',
            }),
            'notes': forms.Textarea(attrs={
                'class': _TEXTAREA,
                'rows': '2',
                'placeholder': 'Breve descrizione dell\'attività (facoltativo)',
            }),
        }
        labels = {
            'date': 'Data',
            'activity_type': 'Tipo',
            'dm55_phase': 'Fase DM55',
            'duration_hours': 'Durata (ore)',
            'notes': 'Note',
        }
