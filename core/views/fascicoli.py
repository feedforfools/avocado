from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from ..models import Activity, Deadline, Fascicolo, FascicoloParty
from ..forms import ActivityForm, DeadlineForm, FascicoloCreateForm


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

_ACTIVITY_COUNT_SQ = Subquery(
    Activity.objects
    .filter(fascicolo=OuterRef('pk'))
    .order_by()
    .values('fascicolo')
    .annotate(c=Count('pk'))
    .values('c')[:1]
)

_NEXT_DEADLINE_DATE_SQ = Subquery(
    Deadline.objects
    .filter(fascicolo=OuterRef('pk'), is_completed=False)
    .order_by('due_date')
    .values('due_date')[:1]
)

_OPEN_DEADLINE_COUNT_SQ = Subquery(
    Deadline.objects
    .filter(fascicolo=OuterRef('pk'), is_completed=False)
    .order_by()
    .values('fascicolo')
    .annotate(c=Count('pk'))
    .values('c')[:1]
)


def _filtered_fascicoli(user, q='', tab='attivi', sort='opened_date', sort_dir='desc'):
    qs = (
        Fascicolo.objects.filter(owner=user)
        .select_related('proceeding_type')
        .prefetch_related('parties__contact')
        .annotate(
            client_last_name=_CLIENT_LAST_NAME_SQ,
            activity_count=_ACTIVITY_COUNT_SQ,
            next_deadline_date=_NEXT_DEADLINE_DATE_SQ,
            open_deadline_count=_OPEN_DEADLINE_COUNT_SQ,
        )
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
            'core/partials/fascicoli/table.html'
            if request.htmx.target == 'fascicoli-table'
            else 'core/partials/fascicoli/body.html'
        )
        return render(request, template, ctx)
    return render(request, 'core/fascicoli.html', ctx)


_VALID_TABS = frozenset({'panoramica', 'attivita', 'scadenze', 'documenti', 'parcella'})
_PARTY_ROLE_ORDER = ['client', 'opposing_party', 'opposing_counsel', 'expert_witness', 'judge', 'other']


def _fascicolo_with_parties(pk, user):
    return get_object_or_404(
        Fascicolo.objects.select_related('proceeding_type').prefetch_related('parties__contact'),
        pk=pk,
        owner=user,
    )


def _sorted_parties(fascicolo):
    return sorted(
        fascicolo.parties.all(),
        key=lambda p: _PARTY_ROLE_ORDER.index(p.role) if p.role in _PARTY_ROLE_ORDER else len(_PARTY_ROLE_ORDER),
    )


@login_required
def fascicolo_detail(request, pk):
    fascicolo = _fascicolo_with_parties(pk, request.user)
    return render(request, 'core/fascicolo_detail.html', {
        'fascicolo': fascicolo,
        'parties': _sorted_parties(fascicolo),
        'active_tab': 'panoramica',
        **_panoramica_ctx(fascicolo),
    })


def _panoramica_ctx(fascicolo):
    """Context data for the Panoramica tab — shared by fascicolo_detail and fascicolo_tab."""
    today = date.today()
    return {
        'activity_count': Activity.objects.filter(fascicolo=fascicolo).count(),
        'deadline_count': Deadline.objects.filter(fascicolo=fascicolo, is_completed=False).count(),
        'next_deadline': (
            Deadline.objects
            .filter(fascicolo=fascicolo, is_completed=False)
            .order_by('due_date')
            .first()
        ),
        'today': today,
        'today_plus_7': today + timedelta(days=7),
    }


@login_required
def fascicolo_tab(request, pk, tab):
    if tab not in _VALID_TABS:
        raise Http404
    fascicolo = _fascicolo_with_parties(pk, request.user)
    ctx = {
        'fascicolo': fascicolo,
        'active_tab': tab,
    }
    if tab == 'attivita':
        ctx['activities'] = Activity.objects.filter(fascicolo=fascicolo)
    elif tab == 'panoramica':
        ctx.update(_panoramica_ctx(fascicolo))
    elif tab == 'scadenze':
        deadlines_qs = Deadline.objects.filter(fascicolo=fascicolo).order_by('is_completed', 'due_date')
        ctx['deadlines_template'] = deadlines_qs.filter(source='template')
        ctx['deadlines_manual'] = deadlines_qs.filter(source='manual')
    return render(request, f'core/partials/fascicolo/tab_{tab}.html', ctx)


@login_required
def activity_form_modal(request, pk):
    fascicolo = get_object_or_404(Fascicolo, pk=pk, owner=request.user)
    return render(request, 'core/partials/fascicolo/activity_form_modal.html', {
        'fascicolo': fascicolo,
        'form': ActivityForm(),
    })


@login_required
@require_POST
def activity_create(request, pk):
    fascicolo = get_object_or_404(Fascicolo, pk=pk, owner=request.user)
    form = ActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.fascicolo = fascicolo
        activity.save()
        return HttpResponse(headers={'HX-Trigger': 'activityCreated'})
    return render(request, 'core/partials/fascicolo/activity_form_modal.html', {
        'fascicolo': fascicolo,
        'form': form,
    })


@login_required
def fascicolo_create(request):
    if request.method == 'POST':
        form = FascicoloCreateForm(request.POST, user=request.user)
        if form.is_valid():
            cd = form.cleaned_data
            with transaction.atomic():
                fascicolo = Fascicolo.objects.create(
                    rg_number=cd['rg_number'],
                    court=cd['court'],
                    proceeding_type=cd['proceeding_type'],
                    status=cd['status'],
                    opened_date=cd['opened_date'],
                    first_hearing_date=cd['first_hearing_date'],
                    custom_title=cd['custom_title'],
                    notes=cd['notes'],
                    owner=request.user,
                )
                if cd.get('client_contact'):
                    FascicoloParty.objects.create(
                        fascicolo=fascicolo,
                        contact=cd['client_contact'],
                        role='client',
                    )
                if cd.get('opposing_party_contact'):
                    FascicoloParty.objects.create(
                        fascicolo=fascicolo,
                        contact=cd['opposing_party_contact'],
                        role='opposing_party',
                    )
                # auto_title depends on parties — recompute after parties are saved
                fascicolo.refresh_auto_title()
            return redirect('core:fascicolo_detail', pk=fascicolo.pk)
    else:
        form = FascicoloCreateForm(user=request.user)
    return render(request, 'core/fascicolo_create.html', {'form': form})


# ---------------------------------------------------------------------------
# Scadenze (Deadlines) — fascicolo-scoped
# ---------------------------------------------------------------------------

@login_required
def deadline_form_modal(request, pk):
    fascicolo = get_object_or_404(Fascicolo, pk=pk, owner=request.user)
    return render(request, 'core/partials/fascicolo/deadline_form_modal.html', {
        'fascicolo': fascicolo,
        'form': DeadlineForm(),
    })


@login_required
@require_POST
def deadline_create(request, pk):
    fascicolo = get_object_or_404(Fascicolo, pk=pk, owner=request.user)
    form = DeadlineForm(request.POST)
    if form.is_valid():
        deadline = form.save(commit=False)
        deadline.fascicolo = fascicolo
        deadline.source = 'manual'
        deadline.save()
        return HttpResponse(headers={'HX-Trigger': 'deadlineChanged'})
    return render(request, 'core/partials/fascicolo/deadline_form_modal.html', {
        'fascicolo': fascicolo,
        'form': form,
    })


@login_required
@require_POST
def deadline_toggle_complete(request, pk, deadline_pk):
    fascicolo = get_object_or_404(Fascicolo, pk=pk, owner=request.user)
    deadline = get_object_or_404(Deadline, pk=deadline_pk, fascicolo=fascicolo)
    deadline.is_completed = not deadline.is_completed
    deadline.save(update_fields=['is_completed', 'updated_at'])
    return HttpResponse(headers={'HX-Trigger': 'deadlineChanged'})
