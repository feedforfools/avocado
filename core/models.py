from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


class Contact(models.Model):
    ROLE_CHOICES = [
        ('client', 'Cliente'),
        ('opposing_party', 'Controparte'),
        ('lawyer', 'Avvocato'),
        ('consultant', 'Consulente'),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contacts',
    )
    favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self) -> str:
        return f"{self.first_name[0]}{self.last_name[0]}".upper()


class ProceedingType(models.Model):
    """Proceeding type (e.g. Civil, Labour, Family, Criminal).

    Seeded via fixture. Admins can add/edit rows without a deploy.
    """

    name = models.CharField('Nome', max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField('Descrizione', blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tipo procedimento'
        verbose_name_plural = 'Tipi procedimento'

    def __str__(self) -> str:
        return self.name


class DeadlineRule(models.Model):
    """One deterministic deadline rule relative to an anchor date.

    Used to auto-generate Deadline records when an anchor date is set on a
    Fascicolo.  offset_days is positive for dates *after* the anchor and
    negative for dates *before* it.
    """

    proceeding_type = models.ForeignKey(
        ProceedingType,
        on_delete=models.CASCADE,
        related_name='rules',
    )
    label = models.CharField('Descrizione', max_length=200)
    anchor = models.CharField(
        'Ancora',
        max_length=50,
        help_text='Name of the date field on Fascicolo used as the reference point (e.g. first_hearing_date)',
    )
    offset_days = models.IntegerField(
        'Scostamento (giorni)',
        help_text='Positivo = dopo l\'ancora, negativo = prima dell\'ancora',
    )
    reminder_days_before = models.JSONField(
        'Promemoria (giorni prima)',
        default=list,
        help_text='Es. [7, 3, 1]',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['anchor', 'offset_days']
        verbose_name = 'Regola scadenza'
        verbose_name_plural = 'Regole scadenze'

    def __str__(self) -> str:
        direction = 'after' if self.offset_days >= 0 else 'before'
        return f"{self.label} ({abs(self.offset_days)}d {direction} {self.anchor})"


class Fascicolo(models.Model):
    """The case file — the central object of the application.

    Every other entity (activities, deadlines, documents, invoice) is a
    relation to the Fascicolo.
    """

    STATUS_CHOICES = [
        ('active', 'Attivo'),
        ('suspended', 'Sospeso'),
        ('archived', 'Archiviato'),
    ]

    # Title fields.
    # auto_title is kept in sync by the model; custom_title is an optional
    # free-text override.  Use display_title in templates everywhere.
    auto_title = models.CharField(max_length=255, blank=True)
    custom_title = models.CharField('Titolo personalizzato', max_length=255, blank=True)

    # Core case fields.
    rg_number = models.CharField(
        'RG',
        max_length=50,
        blank=True,
        help_text='Numero di Registro Generale (es. 1234/2025)',
    )
    court = models.CharField('Tribunale', max_length=100, blank=True)
    proceeding_type = models.ForeignKey(
        ProceedingType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='fascicoli',
        verbose_name='Tipo procedimento',
    )
    status = models.CharField(
        'Stato',
        max_length=12,
        choices=STATUS_CHOICES,
        default='active',
    )
    opened_date = models.DateField('Data apertura')
    first_hearing_date = models.DateField('Prima udienza', null=True, blank=True)
    notes = models.TextField('Note', blank=True)

    # Ownership — to be replaced by a studio FK post-MVP.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fascicoli',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reverse relation declared for static analysis; populated by FascicoloParty.
    if TYPE_CHECKING:
        parties: RelatedManager[FascicoloParty]

    class Meta:
        ordering = ['-opened_date', '-created_at']
        verbose_name = 'Fascicolo'
        verbose_name_plural = 'Fascicoli'

    def __str__(self) -> str:
        return self.display_title

    @property
    def display_title(self) -> str:
        """Return custom_title if set, otherwise auto_title."""
        return self.custom_title if self.custom_title else self.auto_title

    def _compute_auto_title_value(self) -> str:
        """Build the Italian-convention title from parties, court, and year.

        Format: «<client_last_name> c/ <opposing_last_name> – Trib. <court> <year>»
        Falls back gracefully when parties or court are not yet set.
        """
        try:
            parties = list(self.parties.select_related('contact').all())
        except Exception:
            parties = []

        client = next((p for p in parties if p.role == 'client'), None)
        opposing = next((p for p in parties if p.role == 'opposing_party'), None)

        name_part = ''
        if client and opposing:
            name_part = f"{client.contact.last_name} c/ {opposing.contact.last_name}"
        elif client:
            name_part = client.contact.last_name

        year = str(self.opened_date.year) if self.opened_date else ''
        court = self.court or ''
        suffix_tokens = [t for t in ['Trib.', court, year] if t]
        suffix = ' '.join(suffix_tokens)

        if name_part and suffix:
            return f"{name_part} – {suffix}"
        return name_part or suffix

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.auto_title = self._compute_auto_title_value()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def refresh_auto_title(self) -> None:
        """Recompute and persist auto_title after related parties change.

        Uses a targeted UPDATE to avoid triggering the full save() cycle
        (and its side effects like updated_at bumping).
        """
        new_title = self._compute_auto_title_value()
        self.auto_title = new_title
        type(self).objects.filter(pk=self.pk).update(auto_title=new_title)


class FascicoloParty(models.Model):
    """Through model linking a Contact to a Fascicolo with a per-case role.

    A contact can appear with multiple roles inside one case (unusual but
    valid) and with different roles across cases — these do not conflict.
    """

    ROLE_CHOICES = [
        ('client', 'Assistito'),
        ('opposing_party', 'Controparte'),
        ('opposing_counsel', 'Avvocato di controparte'),
        ('expert_witness', 'Consulente tecnico'),
        ('judge', 'Giudice'),
        ('other', 'Altro'),
    ]

    fascicolo = models.ForeignKey(
        Fascicolo,
        on_delete=models.CASCADE,
        related_name='parties',
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name='fascicolo_roles',
    )
    role = models.CharField('Ruolo', max_length=20, choices=ROLE_CHOICES)

    class Meta:
        unique_together = [('fascicolo', 'contact', 'role')]
        verbose_name = 'Parte del fascicolo'
        verbose_name_plural = 'Parti del fascicolo'

    def __str__(self) -> str:
        role_label = self.get_role_display()  # type: ignore[attr-defined]
        return f"{self.contact} – {role_label} in {self.fascicolo}"

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
        self.fascicolo.refresh_auto_title()

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        fascicolo = self.fascicolo
        result = super().delete(using=using, keep_parents=keep_parents)
        fascicolo.refresh_auto_title()
        return result


class Activity(models.Model):
    """A single time-stamped activity entry on a Fascicolo.

    Used as the source of truth for the Parcella (invoice) draft.
    dm55_phase is a strict choice field — never free text — because it is
    the key that drives the DM55/2014 tariff engine.
    """

    ACTIVITY_TYPE_CHOICES = [
        ('udienza', 'Udienza'),
        ('studio', 'Studio'),
        ('redazione', 'Redazione atti'),
        ('corrispondenza', 'Corrispondenza'),
        ('consulenza', 'Consulenza'),
        ('telefonate', 'Telefonate'),
        ('riunione', 'Riunione'),
        ('altro', 'Altro'),
    ]

    DM55_PHASE_CHOICES = [
        ('studio', 'Fase di studio'),
        ('introduttiva', 'Fase introduttiva'),
        ('istruttoria', 'Fase istruttoria'),
        ('decisionale', 'Fase decisionale'),
    ]

    fascicolo = models.ForeignKey(
        Fascicolo,
        on_delete=models.CASCADE,
        related_name='activities',
    )
    date = models.DateField('Data')
    activity_type = models.CharField('Tipo', max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    dm55_phase = models.CharField('Fase DM55', max_length=15, choices=DM55_PHASE_CHOICES)
    duration_hours = models.DecimalField('Durata (ore)', max_digits=5, decimal_places=2)
    notes = models.TextField('Note', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Attività'
        verbose_name_plural = 'Attività'

    def __str__(self) -> str:
        return f"{self.get_activity_type_display()} – {self.date}"  # type: ignore[attr-defined]