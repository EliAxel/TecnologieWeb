from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
import re
from django.core.exceptions import ValidationError

# Project specific
from django.conf import settings
from sylvelius.models import (
    Ordine,
    Prodotto,
    Annuncio
)
from sylvelius.views import create_notification
from .models import Invoice, Iban
from progetto_tw.constants import MIN_ORDN_QUANTITA_VALUE
from progetto_tw.mixins import CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin
# Other
import json
import uuid
import requests
from requests.auth import HTTPBasicAuth
from django.core.exceptions import PermissionDenied

# Create your views here.
class PurchasePageView(CustomLoginRequiredMixin,ModeratoreAccessForbiddenMixin,View):
    template_name="purchase/payment_process.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        context = {}
        annuncio_id = self.request.GET.get("annuncio_id")
        annuncio = get_object_or_404(Annuncio,uuid=annuncio_id,is_published=True)
        amount = annuncio.prodotto.prezzo
        item_name = annuncio.prodotto.nome
        product_id = annuncio.prodotto.id #type:ignore
        quantita = self.request.GET.get("quantita", f"{MIN_ORDN_QUANTITA_VALUE}") 
        user_id = self.request.user.id#type:ignore
        invoice_id = str(uuid.uuid4())
        if int(quantita) > annuncio.qta_magazzino:
            return redirect(f'{reverse("sylvelius:dettagli_annuncio",kwargs={"uuid": annuncio_id})}?evento=ordine_grosso')
        elif int(quantita) < 1:
            return redirect(f'{reverse("sylvelius:dettagli_annuncio",kwargs={"uuid": annuncio_id})}?evento=ordine_piccolo')
        
        invoice_obj =Invoice.objects.create(
                        invoice_id = invoice_id,
                        user_id=user_id,
                        quantita=quantita,
                        prodotto_id=product_id
                    )
        invoice_obj.save()
        
        context["amount"] = amount * int(quantita)
        context["item_name"] = item_name
        context["invoice_id"] = invoice_id
        context["quantity"] = quantita
        context["paypal_client_id"] = settings.xxx
        return render(request, self.template_name,context)

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
            
            try:
                annuncio=Annuncio.objects.get(prodotto=prodotto)
            except Annuncio.DoesNotExist:
                return HttpResponse(status=404)
            
            if(annuncio.qta_magazzino < quantita):
                create_notification(recipient=user,title="Acquisto Annullato",
                                    message=f"Purtroppo l'acquisto non è andato a buon fine, le scorte del prodotto {prodotto.nome} in magazzino sono finite. Le arriverà un rimborso completo il prima possibile.")
                stato="annullato"
            else:
                annuncio.qta_magazzino = annuncio.qta_magazzino-quantita
                annuncio.save()
                stato="da spedire"
            
            # Cerchiamo l'ordine completato
            ordine = Ordine.objects.create(
                utente=user,
                prodotto=prodotto,
                quantita=quantita,
                invoice=invoice,
                stato_consegna=stato
            )
            ordine.save()
            create_notification(recipient=user,title="Acquisto Confermato!",message=f"L'acquisto di {prodotto.nome} è andato a buon fine!")
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
                create_notification(recipient=ordine.prodotto.annunci.inserzionista,title="Un utente ha acquistato!",message=f"Un utente ha acquistato {ordine.quantita} unità di {ordine.prodotto.nome}!") #type:ignore
            else:
                return HttpResponse(status=102)

            return HttpResponse(status=200)
        return HttpResponse(status=400)

    except Exception as e:
        return HttpResponse(status=500)

class SetupIban(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin,TemplateView):
    template_name = "purchase/setup_iban.html"
    login_url = reverse_lazy('sylvelius:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        if hasattr(self.request.user, 'iban') and self.request.user.iban: #type: ignore
            context["iban"] = self.request.user.iban #type: ignore
        return context

    def validate_iban(self,iban):
        # Rimuovi spazi e converti in maiuscolo
        iban = iban.replace(' ', '').upper()
        
        # Verifica la struttura base con regex
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$', iban):
            raise ValidationError('form')
        
        # Sposta i primi 4 caratteri alla fine
        rearranged = iban[4:] + iban[:4]
        
        # Converti le lettere in numeri (A=10, B=11, ..., Z=35)
        digits = []
        for char in rearranged:
            if char.isdigit():
                digits.append(char)
            else:
                digits.append(str(10 + ord(char) - ord('A')))
        
        # Unisci tutto in una stringa numerica e calcola il modulo 97
        numeric_iban = int(''.join(digits))
        if numeric_iban % 97 != 1:
            raise ValidationError('contr')

    def post(self, request):
        iban = request.POST.get('iban')
        
        try:
            self.validate_iban(iban)
            Iban.objects.update_or_create(utente=request.user,defaults={'iban':iban})
            # Restituisci una risposta di successo
        except ValidationError as e:
            # Restituisci una risposta di errore con il messaggio
            return render(request,self.template_name,{'notok':str(e)})
        return redirect(f'{reverse("sylvelius:profile_annunci")}?evento=iban_imp')
    
