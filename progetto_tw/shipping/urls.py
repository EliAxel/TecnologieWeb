from django.urls import path, re_path
from . import views

app_name = "shipping"

urlpatterns = [
    re_path(r'^$|^/$', views.SpedizionePageView.as_view(), name='ship'),
    path('spedito/<int:ordine_id>/',views.imposta_spedito, name="imposta_spedito"),
    path('completato/<int:ordine_id>/',views.imposta_completato, name="imposta_completato"),
]