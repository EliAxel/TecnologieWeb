from django.urls import path, re_path
from . import views

app_name = "purchase"

urlpatterns = [
    re_path(r'^$|^/$', views.PurchasePageView.as_view(), name='purchase'),
    path('confermato/', views.payment_done, name='payment_done'),
    path('annullato/', views.payment_cancelled, name='payment_cancelled'),
    path('paypal/coa/', views.paypal_coa, name='paypal_webhook'),
    path('setup_iban/', views.SetupIban.as_view(), name='setup_iban'),
]