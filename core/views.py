from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Contact
from .forms import ContactForm

def index(request):
    if request.htmx:
        return render(request, 'core/partials/greeting.html')
    return render(request, 'core/index.html')

@ensure_csrf_cookie
def contacts(request):
    q = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'tutti')
    sort = request.GET.get('sort', 'name')
    sort_dir = request.GET.get('sort_dir', 'asc')

    contact_list = _filtered_contacts(q, tab, sort, sort_dir)

    paginator = Paginator(contact_list, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    ctx = {
        'page_obj': page_obj,
        'search_query': q,
        'active_tab': tab,
        'sort': sort,
        'sort_dir': sort_dir,
    }
    if request.htmx:
        template = 'core/partials/contacts_table.html' if request.htmx.target == 'contacts-table' else 'core/partials/contacts_body.html'
        return render(request, template, ctx)
    return render(request, 'core/contacts.html', ctx)


@require_POST
def contact_toggle_favorite(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.favorite = not contact.favorite
    contact.save(update_fields=['favorite'])
    return render(request, 'core/partials/contact_row.html', {'contact': contact})


@require_POST
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.delete()
    return render(request, 'core/partials/contacts_body.html', _contacts_ctx(request))


SORT_FIELDS = {
    'name': ('last_name', 'first_name'),
    'role': ('role',),
    'email': ('email',),
    'phone': ('phone_number',),
    'address': ('address',),
}


def _filtered_contacts(q='', tab='tutti', sort='name', sort_dir='asc'):
    contact_list = Contact.objects.all()
    if q:
        contact_list = contact_list.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone_number__icontains=q)
            | Q(address__icontains=q)
        )
    if tab == 'preferiti':
        contact_list = contact_list.filter(favorite=True)
    fields = SORT_FIELDS.get(sort, SORT_FIELDS['name'])
    if sort_dir == 'desc':
        fields = tuple(f'-{f}' for f in fields)
    return contact_list.order_by(*fields)


def _contacts_ctx(request):
    q = (request.POST.get('q') or request.GET.get('q', '')).strip()
    tab = request.POST.get('tab') or request.GET.get('tab', 'tutti')
    sort = request.POST.get('sort') or request.GET.get('sort', 'name')
    sort_dir = request.POST.get('sort_dir') or request.GET.get('sort_dir', 'asc')
    contact_list = _filtered_contacts(q, tab, sort, sort_dir)
    paginator = Paginator(contact_list, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return {
        'page_obj': page_obj,
        'search_query': q,
        'active_tab': tab,
        'sort': sort,
        'sort_dir': sort_dir,
    }


def contact_form_modal(request, pk=None):
    contact = get_object_or_404(Contact, pk=pk) if pk else None
    form = ContactForm(instance=contact)
    return render(request, 'core/partials/contact_form_modal.html', {'form': form})


@require_POST
def contact_create(request):
    form = ContactForm(request.POST)
    if form.is_valid():
        form.save()
        return HttpResponse(headers={'HX-Trigger': 'contacts-changed'})
    return render(request, 'core/partials/contact_form_modal.html', {'form': form})


@require_POST
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = ContactForm(request.POST, instance=contact)
    if form.is_valid():
        form.save()
        return HttpResponse(headers={'HX-Trigger': 'contacts-changed'})
    return render(request, 'core/partials/contact_form_modal.html', {'form': form})