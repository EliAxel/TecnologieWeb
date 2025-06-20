from django.urls import path, re_path
from . import views

app_name = "purchase"

urlpatterns = [
    re_path(r'^$|^/$', views.PurchasePageView.as_view(), name='purchase'),
    path('confermato/', views.payment_done, name='payment_done'),
    path('annullato/', views.payment_cancelled, name='payment_cancelled'),
    path('paypal/coa/', views.paypal_coa, name='paypal_webhook'),
    path('setup_iban/', views.SetupIban.as_view(), name='setup_iban'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('carrello/', views.CarrelloPageView.as_view(), name='carrello'),
    path('checkout/', views.CheckoutPageView.as_view(), name='checkout'),
    path('aumenta_cart/<str:invoice_id>/', views.aumenta_carrello, name='aumenta_carrello'),
    path('diminuisci_cart/<str:invoice_id>/', views.diminuisci_carrello, name='diminuisci_carrello'),
    path('rimuovi_da_cart/<str:invoice_id>/', views.rimuovi_da_carrello, name='rimuovi_da_carrello'),
]