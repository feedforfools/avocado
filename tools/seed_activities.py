"""One-off script to seed 3–8 activities per fascicolo. Run with: python manage.py shell < tools/seed_activities.py"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from core.models import Activity, Fascicolo

User = get_user_model()
owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
if owner is None:
    raise RuntimeError("No users found. Run: python manage.py createsuperuser")

fascicoli = list(Fascicolo.objects.filter(owner=owner))
if not fascicoli:
    raise RuntimeError(
        "No fascicoli found. Run: python manage.py shell < tools/seed_fascicoli.py"
    )

ACTIVITY_TYPES = ['udienza', 'studio', 'redazione', 'corrispondenza', 'consulenza', 'telefonate', 'riunione', 'altro']
DM55_PHASES    = ['studio', 'introduttiva', 'istruttoria', 'decisionale']

# Realistic phase progression: early fascicoli lean toward studio/introduttiva,
# active ones span all phases. We bias by picking a random phase window per fascicolo.
PHASE_WINDOWS = [
    ['studio', 'studio', 'introduttiva'],
    ['studio', 'introduttiva', 'introduttiva', 'istruttoria'],
    ['introduttiva', 'istruttoria', 'istruttoria', 'decisionale'],
    ['istruttoria', 'istruttoria', 'decisionale', 'decisionale'],
    DM55_PHASES,  # fully mixed
]

# Plausible durations in 0.25h increments, weighted toward short sessions
DURATIONS = [0.25, 0.5, 0.75, 1.0, 1.0, 1.25, 1.5, 1.5, 2.0, 2.0, 2.5, 3.0, 3.5, 4.0]

NOTES_BY_TYPE = {
    'udienza':       ['Prima udienza di trattazione.', 'Udienza istruttoria.', 'Udienza decisionale.', 'Rinvio su istanza di parte.', ''],
    'studio':        ['Studio degli atti di causa.', 'Analisi giurisprudenza di riferimento.', 'Studio memoria difensiva.', ''],
    'redazione':     ['Redazione atto di citazione.', 'Redazione memoria ex art. 183 c.p.c.', 'Redazione comparsa di risposta.', 'Redazione istanza al giudice.', ''],
    'corrispondenza':['Corrispondenza con controparte.', 'Comunicazione esito udienza al cliente.', 'Scambio documenti con CTU.', ''],
    'consulenza':    ['Consulenza telefonica con cliente.', 'Incontro in studio con cliente.', 'Aggiornamento situazione processuale.', ''],
    'telefonate':    ['Chiamata con cliente.', 'Contatto con avvocato controparte.', 'Chiamata con cancelleria.', ''],
    'riunione':      ['Riunione preparatoria udienza.', 'Riunione con consulente tecnico.', ''],
    'altro':         ['Accesso agli atti.', 'Notifica a mezzo PEC.', 'Deposito telematico.', ''],
}

total_created = 0

for fascicolo in fascicoli:
    n = random.randint(3, 8)
    phase_pool = random.choice(PHASE_WINDOWS)
    # Spread activities over the period from opened_date to today
    opened = fascicolo.opened_date
    from django.utils import timezone
    span = (timezone.now().date() - opened).days
    if span < 1:
        span = 1

    activities = []
    for _ in range(n):
        offset = random.randint(0, span)
        act_date = opened + timedelta(days=offset)
        act_type = random.choice(ACTIVITY_TYPES)
        activities.append(Activity(
            fascicolo=fascicolo,
            date=act_date,
            activity_type=act_type,
            dm55_phase=random.choice(phase_pool),
            duration_hours=random.choice(DURATIONS),
            notes=random.choice(NOTES_BY_TYPE[act_type]),
        ))

    Activity.objects.bulk_create(activities)
    total_created += len(activities)

print(f"Created {total_created} activities across {len(fascicoli)} fascicoli")
