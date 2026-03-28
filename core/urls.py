from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('fascicoli/', views.fascicoli, name='fascicoli'),
    path('fascicoli/create/', views.fascicolo_create, name='fascicolo_create'),
    path('fascicoli/<int:pk>/', views.fascicolo_detail, name='fascicolo_detail'),
    path('fascicoli/<int:pk>/tabs/<str:tab>/', views.fascicolo_tab, name='fascicolo_tab'),
    path('fascicoli/<int:pk>/attivita/', views.activity_create, name='activity_create'),
    path('fascicoli/<int:pk>/attivita/modal/', views.activity_form_modal, name='activity_form_modal'),
    path('fascicoli/<int:pk>/scadenze/', views.deadline_create, name='deadline_create'),
    path('fascicoli/<int:pk>/scadenze/modal/', views.deadline_form_modal, name='deadline_form_modal'),
    path('fascicoli/<int:pk>/scadenze/<int:deadline_pk>/toggle/', views.deadline_toggle_complete, name='deadline_toggle_complete'),
    path('scadenze/', views.scadenze, name='scadenze'),
    path('scadenze/<int:deadline_pk>/toggle/', views.scadenza_toggle_complete, name='scadenza_toggle_complete'),
    path('contacts/', views.contacts, name='contacts'),
    path('contacts/create/', views.contact_create, name='contact_create'),
    path('contacts/create/modal/', views.contact_form_modal, name='contact_form_modal'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/edit/modal/', views.contact_form_modal, name='contact_edit_modal'),
    path('contacts/<int:pk>/toggle-favorite/', views.contact_toggle_favorite, name='contact_toggle_favorite'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
]