# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_existing_contacts_to_first_superuser(apps, schema_editor):
    """Assign all existing contacts (if any) to the first superuser found."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Contact = apps.get_model('core', 'Contact')
    if not Contact.objects.exists():
        return
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser is None:
        superuser = User.objects.first()
    if superuser is None:
        raise RuntimeError(
            "No users found in the database. "
            "Create a superuser first: python manage.py createsuperuser"
        )
    Contact.objects.filter(owner__isnull=True).update(owner=superuser)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_contact_favorite'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: add nullable so existing rows don't blow up
        migrations.AddField(
            model_name='contact',
            name='owner',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='contacts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Step 2: backfill existing rows
        migrations.RunPython(
            assign_existing_contacts_to_first_superuser,
            reverse_code=migrations.RunPython.noop,
        ),
        # Step 3: make non-nullable now that all rows have an owner
        migrations.AlterField(
            model_name='contact',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='contacts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
