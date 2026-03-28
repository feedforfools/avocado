from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from ..models import Deadline


_SCADENZE_SORT_FIELDS = {
    'due_date': ('due_date',),
    'label':    ('label',),
    'fascicolo': ('fascicolo__auto_title', 'fascicolo__custom_title'),
    'source':   ('source',),
}


def _filtered_scadenze(user, q='', tab='aperte', sort='due_date', sort_dir='asc'):
    qs = (
        Deadline.objects
        .filter(fascicolo__owner=user)
        .select_related('fascicolo', 'fascicolo__proceeding_type')
    )
    if tab == 'aperte':
        qs = qs.filter(is_completed=False)
    elif tab == 'completate':
        qs = qs.filter(is_completed=True)
    elif tab == 'scadute':
        qs = qs.filter(is_completed=False, due_date__lt=date.today())
    elif tab == 'in_scadenza':
        today = date.today()
        qs = qs.filter(is_completed=False, due_date__gte=today, due_date__lte=today + timedelta(days=7))
    # tab == 'tutte': no filter
    if q:
        qs = qs.filter(
            Q(label__icontains=q)
            | Q(notes__icontains=q)
            | Q(fascicolo__auto_title__icontains=q)
            | Q(fascicolo__custom_title__icontains=q)
            | Q(fascicolo__rg_number__icontains=q)
        )
    fields = _SCADENZE_SORT_FIELDS.get(sort, _SCADENZE_SORT_FIELDS['due_date'])
    if sort_dir == 'desc':
        fields = tuple(f'-{f}' for f in fields)
    return qs.order_by(*fields)


def _scadenze_ctx(request):
    q = (request.POST.get('q') or request.GET.get('q', '')).strip()
    tab = request.POST.get('tab') or request.GET.get('tab', 'aperte')
    sort = request.POST.get('sort') or request.GET.get('sort', 'due_date')
    sort_dir = request.POST.get('sort_dir') or request.GET.get('sort_dir', 'asc')
    qs = _filtered_scadenze(request.user, q, tab, sort, sort_dir)
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    today = date.today()
    return {
        'page_obj': page_obj,
        'search_query': q,
        'active_tab': tab,
        'sort': sort,
        'sort_dir': sort_dir,
        'today': today,
        'today_plus_7': today + timedelta(days=7),
    }


@login_required
@ensure_csrf_cookie
def scadenze(request):
    ctx = _scadenze_ctx(request)
    if request.htmx:
        template = (
            'core/partials/scadenze/table.html'
            if request.htmx.target == 'scadenze-table'
            else 'core/partials/scadenze/body.html'
        )
        return render(request, template, ctx)
    return render(request, 'core/scadenze.html', ctx)


@login_required
@require_POST
def scadenza_toggle_complete(request, deadline_pk):
    """Toggle complete on a deadline from the standalone scadenze list."""
    deadline = get_object_or_404(Deadline, pk=deadline_pk, fascicolo__owner=request.user)
    deadline.is_completed = not deadline.is_completed
    deadline.save(update_fields=['is_completed', 'updated_at'])
    return HttpResponse(headers={'HX-Trigger': 'scadenzeChanged'})
