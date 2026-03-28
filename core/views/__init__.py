from .home import index
from .contacts import (
    contacts,
    contact_create,
    contact_delete,
    contact_edit,
    contact_form_modal,
    contact_toggle_favorite,
    _filtered_contacts,
)
from .fascicoli import (
    fascicoli,
    fascicolo_create,
    fascicolo_detail,
    fascicolo_tab,
    activity_create,
    activity_form_modal,
    deadline_create,
    deadline_form_modal,
    deadline_toggle_complete,
)
from .scadenze import (
    scadenze,
    scadenza_toggle_complete,
)

__all__ = [
    'index',
    'contacts',
    'contact_create',
    'contact_delete',
    'contact_edit',
    'contact_form_modal',
    'contact_toggle_favorite',
    '_filtered_contacts',
    'fascicoli',
    'fascicolo_create',
    'fascicolo_detail',
    'fascicolo_tab',
    'activity_create',
    'activity_form_modal',
    'deadline_create',
    'deadline_form_modal',
    'deadline_toggle_complete',
    'scadenze',
    'scadenza_toggle_complete',
]
