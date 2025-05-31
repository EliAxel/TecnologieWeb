from django.urls import path, re_path
from . import views
from .api_views import get_immagine_prodotto, get_immagini_prodotto

app_name = "sylvelius"

urlpatterns = [
    re_path(r"^$|^/$", views.HomePageView.as_view(), name="home"),
    path("register/", views.RegistrazionePageView.as_view(), name="register"),
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("logout/", views.LogoutPageView.as_view(), name="logout"),
    path("account/profilo/", views.ProfiloPageView.as_view(), name="profile"),
    path("account/profilo/modifica/", views.ProfiloEditPageView.as_view(), name="profile_edit"),
    path("account/profilo/elimina/", views.ProfiloDeletePageView.as_view(), name="profile_delete"),
    path("account/profilo/ordini/", views.ProfiloOrdiniPageView.as_view(), name="profile_ordini"),
    path("account/profilo/creazioni/", views.ProfiloCreazioniPageView.as_view(), name="profile_creazioni"),
    path("account/profilo/creazioni/crea/", views.ProfiloCreaCreazionePageView.as_view(), name="crea_annuncio"),
    path("account/profilo/creazioni/nascondi/<int:id>/", views.toggle_pubblicazione , name="nascondi_annuncio"),
    path("account/profilo/creazioni/elimina/<int:id>/", views.delete_pubblicazione, name="elimina_annuncio"),
    path("annuncio/<int:pk>/", views.AnnuncioDetailView.as_view(), name="dettagli_annuncio"),
    path("ricerca/", views.RicercaAnnunciView.as_view(), name="ricerca_annunci"),
    # fbv
    path('check_old_password/', views.check_old_password, name='check_old_password'),
    path("check_username_exists/", views.check_username_exists, name="check_username_exists"),
    path("check_login_credentials/", views.check_login_credentials, name="check_login_credentials"),
    path("aggiungi_commento/<int:annuncio_id>/", views.aggiungi_commento, name="aggiungi_commento"),
    path("modifica_commento/<int:commento_id>/", views.modifica_commento, name="modifica_commento"),
    path("elimina_commento/<int:commento_id>/", views.elimina_commento, name="elimina_commento"),
    # async
    path('api/immagine/<int:prodotto_id>/', get_immagine_prodotto),
    path('api/immagini/<int:prodotto_id>/', get_immagini_prodotto),
    # da spostare
    path('pagamento/', views.fake_purchase, name='fake_purchase'),
    path('pagamento_ok/', views.payment_done, name='payment_done'),
    path('pagamento_nonok/', views.payment_cancelled, name='payment_cancelled'),
    path('paypal/pcc/', views.paypal_pcc, name='paypal_webhook'),
    path('paypal/coa/', views.paypal_coa, name='paypal_webhook'),
]