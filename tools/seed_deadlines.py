"""One-off script to seed 2–5 manual deadlines per fascicolo. Run with: python manage.py shell < tools/seed_deadlines.py"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Deadline, Fascicolo

User = get_user_model()
owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
if owner is None:
    raise RuntimeError("No users found. Run: python manage.py createsuperuser")

fascicoli = list(Fascicolo.objects.filter(owner=owner))
if not fascicoli:
    raise RuntimeError(
        "No fascicoli found. Run: python manage.py shell < tools/seed_fascicoli.py"
    )

today = timezone.now().date()

LABEL_POOL = [
    "Deposito memoria difensiva",
    "Deposito atto di citazione",
    "Comunicazione esito udienza al cliente",
    "Deposito comparsa di risposta",
    "Iscrizione a ruolo",
    "Scadenza opposizione",
    "Notifica atto di appello",
    "Deposito ricorso in cassazione",
    "Deposito istanza di rinvio",
    "Scadenza per il pagamento del contributo unificato",
    "Richiesta estratto di sentenza",
    "Scadenza termine per impugnazione",
    "Deposito documentazione richiesta dal CTU",
    "Pagamento onorari CTU",
    "Scadenza termine art. 183 c.p.c.",
]

total_created = 0

for fascicolo in fascicoli:
    # Delete existing seed deadlines to allow re-running idempotently
    Deadline.objects.filter(fascicolo=fascicolo, source='manual').delete()

    n = random.randint(2, 5)
    labels = random.sample(LABEL_POOL, n)

    deadlines = []
    for label in labels:
        # Scatter due dates: some past (overdue), some near, some future
        offset_days = random.choice([
            -random.randint(1, 30),   # overdue
            random.randint(1, 6),     # soon (≤ 7 days)
            random.randint(7, 90),    # ok — future
            random.randint(7, 90),    # ok — future (weighted)
            random.randint(7, 90),    # ok — future (weighted)
        ])
        due = today + timedelta(days=offset_days)
        is_completed = random.random() < 0.25  # 25% chance already completed

        deadlines.append(Deadline(
            fascicolo=fascicolo,
            label=label,
            due_date=due,
            source='manual',
            is_completed=is_completed,
        ))

    Deadline.objects.bulk_create(deadlines)
    total_created += len(deadlines)
    print(f"  {fascicolo.display_title[:60]}: {len(deadlines)} scadenze")

print(f"\nDone — {total_created} deadlines seeded across {len(fascicoli)} fascicoli.")
