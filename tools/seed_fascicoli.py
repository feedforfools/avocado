"""One-off script to seed 30 fascicoli with parties. Run with: python manage.py shell < tools/seed_fascicoli.py"""
import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from core.models import Contact, Fascicolo, FascicoloParty, ProceedingType

User = get_user_model()
owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
if owner is None:
    raise RuntimeError("No users found. Run: python manage.py createsuperuser")

proceeding_types = list(ProceedingType.objects.filter(is_active=True))
if not proceeding_types:
    raise RuntimeError("No ProceedingTypes found. Run: python manage.py loaddata core/fixtures/proceeding_types.json")

# Build contact pools from existing contacts (seeded by seed_contacts.py).
# Fall back to creating minimal stubs if the contacts table is empty.
clients    = list(Contact.objects.filter(owner=owner, role='client'))
opposites  = list(Contact.objects.filter(owner=owner, role='opposing_party'))
lawyers    = list(Contact.objects.filter(owner=owner, role='lawyer'))

if not clients or not opposites:
    raise RuntimeError(
        "Not enough contacts found. Run: python manage.py shell < tools/seed_contacts.py"
    )

courts = [
    'Trieste', 'Udine', 'Pordenone', 'Gorizia',
    'Padova', 'Venezia', 'Treviso', 'Verona',
]

statuses        = ['active', 'active', 'active', 'suspended', 'archived']
status_weights  = [0.60, 0.60, 0.60, 0.20, 0.10]   # active heavily weighted

rg_years = [2023, 2024, 2025, 2026]

today = date.today()


def random_past_date(years_back=3):
    delta = random.randint(0, years_back * 365)
    return today - timedelta(days=delta)


def random_future_date(days_ahead=180):
    delta = random.randint(7, days_ahead)
    return today + timedelta(days=delta)


created = 0
for _ in range(30):
    client   = random.choice(clients)
    opposite = random.choice([c for c in opposites if c != client] or opposites)
    court    = random.choice(courts)
    pt       = random.choice(proceeding_types)
    status   = random.choices(statuses, weights=status_weights, k=1)[0]
    rg_year  = random.choice(rg_years)
    rg_num   = f"{random.randint(100, 9999)}/{rg_year}"
    opened   = random_past_date()
    hearing  = random_future_date() if random.random() < 0.6 else None

    notes_options = [
        '',
        'Cliente difficile da raggiungere. Preferisce WhatsApp.',
        'Causa complessa. Perizia tecnica in corso.',
        'In attesa di documentazione dal cliente.',
        'Udienza rinviata su istanza di parte.',
        'Accordo transattivo in discussione.',
    ]

    fascicolo = Fascicolo(
        rg_number=rg_num,
        court=court,
        proceeding_type=pt,
        status=status,
        opened_date=opened,
        first_hearing_date=hearing,
        notes=random.choice(notes_options),
        owner=owner,
    )
    fascicolo.save()

    FascicoloParty.objects.create(fascicolo=fascicolo, contact=client,   role='client')
    FascicoloParty.objects.create(fascicolo=fascicolo, contact=opposite, role='opposing_party')

    # Optionally add opposing counsel (~50% of cases)
    if lawyers and random.random() < 0.5:
        counsel = random.choice(lawyers)
        FascicoloParty.objects.get_or_create(fascicolo=fascicolo, contact=counsel, role='opposing_counsel')

    created += 1

print(f"Created {created} fascicoli (total: {Fascicolo.objects.filter(owner=owner).count()})")
