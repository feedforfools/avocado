from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, Subquery
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Contact, Fascicolo, FascicoloParty
from .forms import ContactForm

@login_required
def index(request):
    if request.htmx:
        return render(request, 'core/partials/greeting.html')
    return render(request, 'core/index.html')

@login_required
@ensure_csrf_cookie
def contacts(request):
    q = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'tutti')
    sort = request.GET.get('sort', 'name')
    sort_dir = request.GET.get('sort_dir', 'asc')

    contact_list = _filtered_contacts(request.user, q, tab, sort, sort_dir)

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


@login_required
@require_POST
def contact_toggle_favorite(request, pk):
    contact = get_object_or_404(Contact, pk=pk, owner=request.user)
    contact.favorite = not contact.favorite
    contact.save(update_fields=['favorite'])
    return render(request, 'core/partials/contact_row.html', {'contact': contact})


@login_required
@require_POST
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk, owner=request.user)
    contact.delete()
    return render(request, 'core/partials/contacts_body.html', _contacts_ctx(request))


SORT_FIELDS = {
    'name': ('last_name', 'first_name'),
    'role': ('role',),
    'email': ('email',),
    'phone': ('phone_number',),
    'address': ('address',),
}


def _filtered_contacts(user, q='', tab='tutti', sort='name', sort_dir='asc'):
    contact_list = Contact.objects.filter(owner=user)
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
    contact_list = _filtered_contacts(request.user, q, tab, sort, sort_dir)
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


@login_required
def contact_form_modal(request, pk=None):
    contact = get_object_or_404(Contact, pk=pk, owner=request.user) if pk else None
    form = ContactForm(instance=contact)
    return render(request, 'core/partials/contact_form_modal.html', {'form': form})


@login_required
@require_POST
def contact_create(request):
    form = ContactForm(request.POST)
    if form.is_valid():
        contact = form.save(commit=False)
        contact.owner = request.user
        contact.save()
        return HttpResponse(headers={'HX-Trigger': 'contacts-changed'})
    return render(request, 'core/partials/contact_form_modal.html', {'form': form})


@login_required
@require_POST
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk, owner=request.user)
    form = ContactForm(request.POST, instance=contact)
    if form.is_valid():
        form.save()
        return HttpResponse(headers={'HX-Trigger': 'contacts-changed'})
    return render(request, 'core/partials/contact_form_modal.html', {'form': form})


# ---------------------------------------------------------------------------
# Fascicoli
# ---------------------------------------------------------------------------

FASCICOLO_SORT_FIELDS = {
    'title': ('auto_title',),
    'client': ('client_last_name',),
    'opened_date': ('opened_date',),
    'status': ('status',),
    'proceeding_type': ('proceeding_type__name',),
}

_CLIENT_LAST_NAME_SQ = Subquery(
    FascicoloParty.objects.filter(fascicolo=OuterRef('pk'), role='client')
    .values('contact__last_name')[:1]
)


def _filtered_fascicoli(user, q='', tab='attivi', sort='opened_date', sort_dir='desc'):
    qs = (
        Fascicolo.objects.filter(owner=user)
        .select_related('proceeding_type')
        .prefetch_related('parties__contact')
        .annotate(client_last_name=_CLIENT_LAST_NAME_SQ)
    )
    if tab == 'attivi':
        qs = qs.filter(status='active')
    elif tab == 'sospesi':
        qs = qs.filter(status='suspended')
    elif tab == 'archiviati':
        qs = qs.filter(status='archived')
    # tab == 'tutti': no status filter
    if q:
        qs = qs.filter(
            Q(auto_title__icontains=q)
            | Q(custom_title__icontains=q)
            | Q(rg_number__icontains=q)
            | Q(parties__contact__last_name__icontains=q)
            | Q(parties__contact__first_name__icontains=q)
        ).distinct()
    fields = FASCICOLO_SORT_FIELDS.get(sort, FASCICOLO_SORT_FIELDS['opened_date'])
    if sort_dir == 'desc':
        fields = tuple(f'-{f}' for f in fields)
    return qs.order_by(*fields)


def _fascicoli_ctx(request):
    q = (request.POST.get('q') or request.GET.get('q', '')).strip()
    tab = request.POST.get('tab') or request.GET.get('tab', 'attivi')
    sort = request.POST.get('sort') or request.GET.get('sort', 'opened_date')
    sort_dir = request.POST.get('sort_dir') or request.GET.get('sort_dir', 'desc')
    qs = _filtered_fascicoli(request.user, q, tab, sort, sort_dir)
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return {
        'page_obj': page_obj,
        'search_query': q,
        'active_tab': tab,
        'sort': sort,
        'sort_dir': sort_dir,
    }


@login_required
@ensure_csrf_cookie
def fascicoli(request):
    ctx = _fascicoli_ctx(request)
    if request.htmx:
        template = (
            'core/partials/fascicoli_table.html'
            if request.htmx.target == 'fascicoli-table'
            else 'core/partials/fascicoli_body.html'
        )
        return render(request, template, ctx)
    return render(request, 'core/fascicoli.html', ctx)


@login_required
def fascicolo_detail(request, pk):
    # Stub — full detail page is the next sprint.
    fascicolo = get_object_or_404(Fascicolo, pk=pk, owner=request.user)
    return HttpResponse(
        f'<p style="font-family:sans-serif;padding:2rem">← <a href="/fascicoli/">Fascicoli</a> &nbsp;|&nbsp; '
        f'<strong>{fascicolo.display_title}</strong> — dettaglio in arrivo.</p>'
    )


@login_required
def fascicolo_create(request):
    # Stub — create form is the next sprint.
    return HttpResponse(
        '<p style="font-family:sans-serif;padding:2rem">'
        '← <a href="/fascicoli/">Fascicoli</a> &nbsp;|&nbsp; Nuovo fascicolo — in arrivo.</p>'
    )