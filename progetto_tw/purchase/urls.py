from django.urls import path, re_path
from . import views

app_name = "purchase"

urlpatterns = [
    re_path(r'^$|^/$', views.fake_purchase, name='fake_purchase'),
    path('confermato/', views.payment_done, name='payment_done'),
    path('annullato/', views.payment_cancelled, name='payment_cancelled'),
    path('paypal/pcc/', views.paypal_pcc, name='paypal_webhook'),
    path('paypal/coa/', views.paypal_coa, name='paypal_webhook'),
]