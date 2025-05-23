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
]