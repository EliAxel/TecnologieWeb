from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render

# Project specific
from django.conf import settings
from sylvelius.models import (
    Ordine,
    Prodotto
)
from .models import Invoice
from progetto_tw.constants import MIN_ORDN_QUANTITA_VALUE

# Other
import json
import uuid
import requests
from requests.auth import HTTPBasicAuth

# Create your views here.
@require_POST
@login_required
def fake_purchase(request):    
    amount = request.POST.get("amount", "0.00")
    item_name = request.POST.get("item_name", "Prodotto sconosciuto")
    product_id = request.POST.get("product_id", "")
    quantity = request.POST.get("quantity", f"{MIN_ORDN_QUANTITA_VALUE}")
    user_id = request.POST.get("user_id")
    invoice_id = str(uuid.uuid4())
    invoice_obj =Invoice.objects.create(
                    invoice_id = invoice_id,
                    user_id=user_id,
                    quantita=quantity,
                    prodotto_id=product_id
                )
    invoice_obj.save()


    if request.method == 'POST':        
        return render(request, "purchase/payment_process.html", {
            "amount": amount,
            "item_name": item_name,
            "invoice_id": invoice_id,
            "quantity": quantity,
            "paypal_client_id": settings.xxx,
        })
    return HttpResponseBadRequest("Metodo non supportato")

def payment_done(request):
    return render(request, 'purchase/payment_done.html')

def payment_cancelled(request):
    return render(request, 'purchase/payment_cancelled.html')
# non callable
def get_paypal_access_token():
    xxx = settings.xxx
    xxx = settings.xxx
    PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  # o sandbox

    response = requests.post(
        f"{PAYPAL_API_BASE}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=HTTPBasicAuth(xxx, xxx),
    )

    response.raise_for_status()
    return response.json()["access_token"]
# non callable
def verify_paypal_webhook(request,body):
    PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com" 
    access_token = get_paypal_access_token()
    headers = request.headers
    webhook_event = json.loads(body)
    event_type = webhook_event.get("event_type")

    # Scegli il webhook_id corretto in base all'evento
    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        webhook_id = settings.PAYPAL_PCC_ID
    elif event_type == "CHECKOUT.ORDER.APPROVED":
        webhook_id = settings.PAYPAL_COA_ID
    else:
        return False
    
    verification_data = {
        "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
        "cert_url": headers.get("PAYPAL-CERT-URL"),
        "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
        "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
        "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
        "webhook_id": webhook_id,  
        "webhook_event": webhook_event,
    }

    response = requests.post(
        f"{PAYPAL_API_BASE}/v1/notifications/verify-webhook-signature",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json=verification_data,
    )

    response.raise_for_status()
    verification_status = response.json().get("verification_status")
    return verification_status == "SUCCESS"

@csrf_exempt
@require_POST
def paypal_pcc(request):    
    body = request.body

    if not verify_paypal_webhook(request,body):
        return HttpResponse(status=401)
    
    try:
        payload = json.loads(body)
        event_type = payload.get('event_type')
        resource = payload.get('resource', {})

        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            invoice = resource.get('invoice_id')
            
            if not invoice:
                return HttpResponse(status=400)

            invoice_obj = Invoice.objects.get(invoice_id=invoice)
            if not invoice_obj:
                return HttpResponse(status=404)
            
            product_id = invoice_obj.prodotto_id
            user_id = invoice_obj.user_id
            quantita = invoice_obj.quantita

            try:
                prodotto = Prodotto.objects.get(id=product_id)
            except Prodotto.DoesNotExist:
                return HttpResponse(status=404)
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return HttpResponse(status=404)
            
            # Cerchiamo l'ordine completato
            ordine = Ordine.objects.create(
                utente=user,
                prodotto=prodotto,
                quantita=quantita,
                invoice=invoice,
            )
            ordine.save()

            return HttpResponse(status=200)
        return HttpResponse(status=400)
    except Exception as e:
        return HttpResponse(status=500)
    
@csrf_exempt
@require_POST
def paypal_coa(request):    
    body = request.body

    if not verify_paypal_webhook(request,body):
        return HttpResponse(status=401)
    
    try:
        payload = json.loads(body)
        event_type = payload.get('event_type')
        resource = payload.get('resource', {})

        if event_type == 'CHECKOUT.ORDER.APPROVED':
            purchase_units = resource.get('purchase_units', [])
            if not purchase_units:
                return HttpResponse(status=400)

            pu = purchase_units[0]  # prendi il primo purchase unit
            invoice = pu.get('invoice_id')
            invoice_obj = Invoice.objects.filter(invoice_id=invoice).first()
            if not invoice_obj:
                return HttpResponse(status=404)
            product_id = invoice_obj.prodotto_id

            if not invoice or not product_id:
                return HttpResponse(status=400)

            try:
                prodotto = Prodotto.objects.get(id=product_id)
            except Prodotto.DoesNotExist:
                return HttpResponse(status=404)

            ordine = Ordine.objects.filter(invoice=invoice, prodotto=prodotto).first()

            if ordine:
                shipping = pu.get('shipping', {})
                address = shipping.get('address', {})
                ordine.luogo_consegna = address
                ordine.save()
                invoice_obj.delete()
            else:
                return HttpResponse(status=102)

            return HttpResponse(status=200)
        return HttpResponse(status=400)

    except Exception as e:
        return HttpResponse(status=500)
