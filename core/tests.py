from django.contrib.auth import get_user_model
from django.test import Client as HttpClient
from django.test import TestCase

from .models import Contact
from .views import _filtered_contacts

User = get_user_model()


def _user(**kwargs):
    defaults = {'username': 'testlawyer', 'password': 'testpass123'}
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _contact(owner, save=True, **overrides):
    """Factory helper — creates a Contact with sensible defaults."""
    defaults = {'first_name': 'Mario', 'last_name': 'Rossi', 'role': 'client', 'owner': owner}
    defaults.update(overrides)
    c = Contact(**defaults)
    if save:
        c.save()
    return c


class FilteredContactsTest(TestCase):
    """Tests for the _filtered_contacts query logic."""

    def setUp(self):
        self.user = _user()
        self.mario = _contact(self.user, first_name='Mario', last_name='Rossi', email='mario@test.it', favorite=True)
        self.giulia = _contact(self.user, first_name='Giulia', last_name='Bianchi', role='lawyer', address='Via Roma 1')
        self.luca = _contact(self.user, first_name='Luca', last_name='Verdi', phone_number='+39 340 111 2222')

    def test_search_matches_name(self):
        qs = _filtered_contacts(self.user, q='rossi')
        self.assertEqual(list(qs), [self.mario])

    def test_search_matches_email(self):
        qs = _filtered_contacts(self.user, q='mario@test')
        self.assertEqual(list(qs), [self.mario])

    def test_search_matches_phone(self):
        qs = _filtered_contacts(self.user, q='340 111')
        self.assertEqual(list(qs), [self.luca])

    def test_search_matches_address(self):
        qs = _filtered_contacts(self.user, q='via roma')
        self.assertEqual(list(qs), [self.giulia])

    def test_search_no_match(self):
        qs = _filtered_contacts(self.user, q='zzzzz')
        self.assertEqual(list(qs), [])

    def test_tab_preferiti(self):
        qs = _filtered_contacts(self.user, tab='preferiti')
        self.assertEqual(list(qs), [self.mario])

    def test_sort_by_role_asc(self):
        qs = _filtered_contacts(self.user, sort='role', sort_dir='asc')
        roles = [c.role for c in qs]
        self.assertEqual(roles, sorted(roles))

    def test_sort_desc(self):
        qs = _filtered_contacts(self.user, sort='name', sort_dir='desc')
        names = [c.last_name for c in qs]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_only_returns_owners_contacts(self):
        other = _user(username='other')
        _contact(other, first_name='Spy', last_name='Contact')
        qs = _filtered_contacts(self.user)
        self.assertNotIn('Spy', [c.first_name for c in qs])


class ContactsViewTest(TestCase):
    """Tests for the HTMX response contract."""

    def setUp(self):
        self.user = _user()
        self.client = HttpClient()
        self.client.force_login(self.user)
        _contact(self.user)

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

    def test_unauthenticated_redirects(self):
        anon = HttpClient()
        r = anon.get('/contacts/')
        self.assertEqual(r.status_code, 302)


class ContactCreateTest(TestCase):

    def setUp(self):
        self.user = _user()
        self.client = HttpClient()
        self.client.force_login(self.user)

    def test_valid_create_triggers_refresh(self):
        r = self.client.post('/contacts/create/', {'first_name': 'Ada', 'last_name': 'Neri', 'role': 'client'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['HX-Trigger'], 'contacts-changed')
        self.assertTrue(Contact.objects.filter(last_name='Neri').exists())

    def test_invalid_create_returns_form_with_errors(self):
        r = self.client.post('/contacts/create/', {'first_name': '', 'last_name': ''})
        self.assertTemplateUsed(r, 'core/partials/contact_form_modal.html')
        self.assertFalse(Contact.objects.exists())


class ContactEditTest(TestCase):

    def setUp(self):
        self.user = _user()
        self.client = HttpClient()
        self.client.force_login(self.user)

    def test_valid_edit_triggers_refresh(self):
        c = _contact(self.user, first_name='Old', last_name='Name')
        r = self.client.post(f'/contacts/{c.pk}/edit/', {'first_name': 'New', 'last_name': 'Name', 'role': 'client'})
        self.assertEqual(r['HX-Trigger'], 'contacts-changed')
        c.refresh_from_db()
        self.assertEqual(c.first_name, 'New')

    def test_invalid_edit_returns_form_with_errors(self):
        c = _contact(self.user)
        r = self.client.post(f'/contacts/{c.pk}/edit/', {'first_name': '', 'last_name': ''})
        self.assertTemplateUsed(r, 'core/partials/contact_form_modal.html')


class ContactToggleFavoriteTest(TestCase):

    def setUp(self):
        self.user = _user()
        self.client = HttpClient()
        self.client.force_login(self.user)

    def test_toggle_flips_value(self):
        c = _contact(self.user, favorite=False)
        self.client.post(f'/contacts/{c.pk}/toggle-favorite/')
        c.refresh_from_db()
        self.assertTrue(c.favorite)

        self.client.post(f'/contacts/{c.pk}/toggle-favorite/')
        c.refresh_from_db()
        self.assertFalse(c.favorite)


class ContactDeleteTest(TestCase):

    def setUp(self):
        self.user = _user()
        self.client = HttpClient()
        self.client.force_login(self.user)

    def test_delete_removes_contact(self):
        c = _contact(self.user)
        self.client.post(f'/contacts/{c.pk}/delete/')
        self.assertFalse(Contact.objects.filter(pk=c.pk).exists())

    def test_delete_nonexistent_returns_404(self):
        r = self.client.post('/contacts/99999/delete/')
        self.assertEqual(r.status_code, 404)

