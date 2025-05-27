from django.urls import path, re_path
from . import views

app_name = "sylvelius"

urlpatterns = [
    re_path(r"^$|^/$", views.HomePageView.as_view(), name="home"),
    path("register/", views.RegistrazionePageView.as_view(), name="register"),
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("logout/", views.LogoutPageView.as_view(), name="logout"),
    path("accounts/profile/", views.ProfiloPageView.as_view(), name="profile"),
    path("accounts/profile/edit/", views.ProfiloEditPageView.as_view(), name="profile_edit"),
    path("accounts/profile/delete/", views.ProfiloDeletePageView.as_view(), name="profile_delete"),
    path("annuncio/<int:pk>/", views.AnnuncioDetailView.as_view(), name="dettagli_annuncio"),
    path("account/profile/ordini/", views.ProfiloOrdiniPageView.as_view(), name="profile_ordini"),
    path("account/profile/creazioni/", views.ProfiloCreazioniPageView.as_view(), name="profile_creazioni"),
    path("account/profile/creazioni/crea/", views.ProfiloCreaCreazionePageView.as_view(), name="crea_annuncio"),
    path("account/profile/creazioni/nascondi/<int:id>/", views.toggle_pubblicazione , name="nascondi_annuncio"),
    path("account/profile/creazioni/elimina/<int:id>/", views.delete_pubblicazione, name="elimina_annuncio"),
    path('check_old_password/', views.check_old_password, name='check_old_password'),
    path("ricerca/", views.RicercaAnnunciView.as_view(), name="ricerca_annunci"),
    path("check_username_exists/", views.check_username_exists, name="check_username_exists"),
    path("check_login_credentials/", views.check_login_credentials, name="check_login_credentials"),
]