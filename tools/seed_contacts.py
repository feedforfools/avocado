"""One-off script to seed 50 random contacts. Run with: python manage.py shell < tools/seed_contacts.py"""
import random

from django.contrib.auth import get_user_model
from core.models import Contact

User = get_user_model()
owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
if owner is None:
    raise RuntimeError("No users found. Run: python manage.py createsuperuser")

first_names = [
    'Marco', 'Giulia', 'Alessandro', 'Francesca', 'Luca', 'Elena', 'Andrea',
    'Chiara', 'Matteo', 'Sara', 'Lorenzo', 'Anna', 'Davide', 'Valentina',
    'Simone', 'Laura', 'Federico', 'Martina', 'Roberto', 'Silvia', 'Giuseppe',
    'Elisa', 'Stefano', 'Giorgia', 'Paolo', 'Alessia', 'Giovanni', 'Federica',
    'Antonio', 'Sofia', 'Riccardo', 'Ilaria', 'Fabio', 'Roberta', 'Massimo',
    'Claudia', 'Enrico', 'Marta', 'Pietro', 'Paola', 'Carlo', 'Monica',
    'Daniele', 'Valeria', 'Alberto', 'Eleonora', 'Nicola', 'Serena',
    'Tommaso', 'Arianna',
]
last_names = [
    'Rossi', 'Russo', 'Ferrari', 'Esposito', 'Bianchi', 'Romano', 'Colombo',
    'Ricci', 'Marino', 'Greco', 'Bruno', 'Gallo', 'Conti', 'De Luca',
    'Mancini', 'Costa', 'Giordano', 'Rizzo', 'Lombardi', 'Moretti',
    'Barbieri', 'Fontana', 'Santoro', 'Mariani', 'Rinaldi', 'Caruso',
    'Ferrara', 'Galli', 'Martini', 'Leone', 'Longo', 'Gentile', 'Martinelli',
    'Vitale', 'Pellegrini', 'Serra', 'Palumbo', 'Marchetti', 'Testa',
    'Farina', 'Basile', 'Benedetti', 'Cattaneo', 'Sala', 'Parisi',
    'Valentini', 'Bianco', 'Montanari', 'Zanetti', 'Piras',
]
cities = [
    'Trieste', 'Udine', 'Pordenone', 'Gorizia', 'Padova',
    'Venezia', 'Treviso', 'Verona', 'Vicenza', 'Belluno',
]
streets = [
    'Via Roma', 'Via Garibaldi', 'Via Mazzini', 'Corso Italia', 'Via Dante',
    'Via Cavour', 'Via Verdi', 'Via Marconi', 'Via San Marco', 'Via Carducci',
    'Via Battisti', 'Via Oberdan', 'Via Diaz',
]
roles = ['cliente', 'controparte', 'avvocato', 'consulente']
role_weights = [0.5, 0.25, 0.15, 0.1]
phone_prefixes = ['340', '347', '328', '333', '349', '338', '320', '345']

contacts = []
used = set()
for _ in range(50):
    while True:
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        if (fn, ln) not in used:
            used.add((fn, ln))
            break
    role = random.choices(roles, weights=role_weights, k=1)[0]
    email = f"{fn.lower()}.{ln.lower().replace(' ', '')}@email.it"
    phone = f"+39 {random.choice(phone_prefixes)} {random.randint(100, 999)} {random.randint(1000, 9999)}"
    addr = f"{random.choice(streets)} {random.randint(1, 120)}, {random.randint(33100, 35100)} {random.choice(cities)}"
    fav = random.random() < 0.15
    contacts.append(Contact(
        first_name=fn, last_name=ln, email=email,
        phone_number=phone, address=addr, role=role, favorite=fav,
        owner=owner,
    ))

Contact.objects.bulk_create(contacts)
print(f"Created {Contact.objects.count()} contacts")
