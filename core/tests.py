from django.test import TestCase

from django.test import TestCase, Client as HttpClient
from .models import Contact


def _contact(save=True, **overrides):
    """Factory helper — creates a Contact with sensible defaults."""
    defaults = {'first_name': 'Mario', 'last_name': 'Rossi', 'role': 'cliente'}
    defaults.update(overrides)
    c = Contact(**defaults)
    if save:
        c.save()
    return c


class FilteredContactsTest(TestCase):
    """Tests for the _filtered_contacts query logic."""

    def setUp(self):
        self.mario = _contact(first_name='Mario', last_name='Rossi', email='mario@test.it', favorite=True)
        self.giulia = _contact(first_name='Giulia', last_name='Bianchi', role='avvocato', address='Via Roma 1')
        self.luca = _contact(first_name='Luca', last_name='Verdi', phone_number='+39 340 111 2222')

    def test_search_matches_name(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(q='rossi')
        self.assertEqual(list(qs), [self.mario])

    def test_search_matches_email(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(q='mario@test')
        self.assertEqual(list(qs), [self.mario])

    def test_search_matches_phone(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(q='340 111')
        self.assertEqual(list(qs), [self.luca])

    def test_search_matches_address(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(q='via roma')
        self.assertEqual(list(qs), [self.giulia])

    def test_search_no_match(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(q='zzzzz')
        self.assertEqual(list(qs), [])

    def test_tab_preferiti(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(tab='preferiti')
        self.assertEqual(list(qs), [self.mario])

    def test_sort_by_role_asc(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(sort='role', sort_dir='asc')
        roles = [c.role for c in qs]
        self.assertEqual(roles, sorted(roles))

    def test_sort_desc(self):
        from .views import _filtered_contacts
        qs = _filtered_contacts(sort='name', sort_dir='desc')
        names = [c.last_name for c in qs]
        self.assertEqual(names, sorted(names, reverse=True))


class ContactsViewTest(TestCase):
    """Tests for the HTMX response contract."""

    def setUp(self):
        self.client = HttpClient()
        _contact()

    def test_full_page_without_htmx(self):
        r = self.client.get('/contacts/')
        self.assertTemplateUsed(r, 'core/contacts.html')

    def test_htmx_returns_partial(self):
        r = self.client.get('/contacts/', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='contacts-body')
        self.assertTemplateUsed(r, 'core/partials/contacts_body.html')
        self.assertNotContains(r, '<html')

    def test_htmx_table_target(self):
        r = self.client.get('/contacts/', HTTP_HX_REQUEST='true', HTTP_HX_TARGET='contacts-table')
        self.assertTemplateUsed(r, 'core/partials/contacts_table.html')


class ContactCreateTest(TestCase):

    def test_valid_create_triggers_refresh(self):
        r = self.client.post('/contacts/create/', {'first_name': 'Ada', 'last_name': 'Neri', 'role': 'cliente'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['HX-Trigger'], 'contacts-changed')
        self.assertTrue(Contact.objects.filter(last_name='Neri').exists())

    def test_invalid_create_returns_form_with_errors(self):
        r = self.client.post('/contacts/create/', {'first_name': '', 'last_name': ''})
        self.assertTemplateUsed(r, 'core/partials/contact_form_modal.html')
        self.assertFalse(Contact.objects.exists())


class ContactEditTest(TestCase):

    def test_valid_edit_triggers_refresh(self):
        c = _contact(first_name='Old', last_name='Name')
        r = self.client.post(f'/contacts/{c.pk}/edit/', {'first_name': 'New', 'last_name': 'Name', 'role': 'cliente'})
        self.assertEqual(r['HX-Trigger'], 'contacts-changed')
        c.refresh_from_db()
        self.assertEqual(c.first_name, 'New')

    def test_invalid_edit_returns_form_with_errors(self):
        c = _contact()
        r = self.client.post(f'/contacts/{c.pk}/edit/', {'first_name': '', 'last_name': ''})
        self.assertTemplateUsed(r, 'core/partials/contact_form_modal.html')


class ContactToggleFavoriteTest(TestCase):

    def test_toggle_flips_value(self):
        c = _contact(favorite=False)
        self.client.post(f'/contacts/{c.pk}/toggle-favorite/')
        c.refresh_from_db()
        self.assertTrue(c.favorite)

        self.client.post(f'/contacts/{c.pk}/toggle-favorite/')
        c.refresh_from_db()
        self.assertFalse(c.favorite)


class ContactDeleteTest(TestCase):

    def test_delete_removes_contact(self):
        c = _contact()
        self.client.post(f'/contacts/{c.pk}/delete/')
        self.assertFalse(Contact.objects.filter(pk=c.pk).exists())

    def test_delete_nonexistent_returns_404(self):
        r = self.client.post('/contacts/99999/delete/')
        self.assertEqual(r.status_code, 404)
