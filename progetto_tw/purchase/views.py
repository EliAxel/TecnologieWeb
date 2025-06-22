from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.core.exceptions import ValidationError

# Project specific
from django.conf import settings
from sylvelius.models import (
    Ordine,
    Annuncio
)
from sylvelius.views import create_notification
from .models import Invoice, Iban, Cart
from progetto_tw.mixins import CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin
# Other
import json
import uuid
import re
import requests
from decimal import Decimal
from requests.auth import HTTPBasicAuth

#non callable
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

def validate_quantity(quantity, annuncio):
    """Valida la quantità e restituisce un redirect in caso di errore o None se tutto ok."""
    try:
        quantity = int(quantity)
    except ValueError:
        return redirect(
            reverse("sylvelius:dettagli_annuncio", kwargs={"uuid": annuncio.uuid}) + 
            "?evento=non_intero"
        )
    
    if quantity > annuncio.qta_magazzino:
        return redirect(
            reverse("sylvelius:dettagli_annuncio", kwargs={"uuid": annuncio.uuid}) + 
            "?evento=ordine_grosso"
        )
    elif quantity < 1:
        return redirect(
            reverse("sylvelius:dettagli_annuncio", kwargs={"uuid": annuncio.uuid}) + 
            "?evento=ordine_piccolo"
        )
    
    return None

def create_invoice(request, annuncio, quantity, cart=None):
    """Crea una nuova fattura e la associa eventualmente a un carrello."""
    invoice_obj = Invoice.objects.create(
        invoice_id=str(uuid.uuid4()),
        user=request.user,
        quantita=quantity,
        prodotto=annuncio.prodotto,
        cart=cart
    )
    return invoice_obj

def get_invoice_data(request):
    """Elabora i dati della richiesta e restituisce annuncio, quantità e eventuale errore."""
    annuncio_id = request.POST.get("annuncio_id")
    if not annuncio_id:
        annuncio_id = request.GET.get("annuncio_id")
    annuncio = get_object_or_404(Annuncio, uuid=annuncio_id, is_published=True)
    quantity = request.POST.get("quantita")
    if not quantity:
        quantity = request.GET.get("quantita")
    # Validazione quantità
    error_redirect = validate_quantity(quantity, annuncio)
    if error_redirect:
        return None, None, error_redirect
    
    return annuncio, int(quantity), None

class PurchasePageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, View):
    template_name = "purchase/payment_process.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        annuncio, quantity, error_redirect = get_invoice_data(request)
        if error_redirect:
            return error_redirect
        
        invoice = create_invoice(request, annuncio, quantity)
        product = annuncio.prodotto # type: ignore
        
        context = {
            "amount": product.prezzo * Decimal(quantity), # type: ignore
            "item_name": product.nome,
            "invoice_id": invoice.invoice_id,
            "quantity": quantity,
            "paypal_client_id": settings.xxx,
        }
        return render(request, self.template_name, context)

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
    webhook_event = json.loads(body)
    event_type = webhook_event.get("event_type")

    # Scegli il webhook_id corretto in base all'evento
    if event_type == "CHECKOUT.ORDER.APPROVED":
        webhook_id = settings.PAYPAL_COA_ID
    else:
        return False
    
    PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com" 
    access_token = get_paypal_access_token()
    headers = request.headers
    
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
# non callable
def invoice_validation(invoice_obj, pu):
    user = invoice_obj.user
    prodotto = invoice_obj.prodotto
    quantita = invoice_obj.quantita

    try:
        annuncio = Annuncio.objects.get(prodotto=prodotto)
    except Annuncio.DoesNotExist:
        create_notification(
            recipient=user,
            title="Acquisto Annullato",
            message=f"Purtroppo l'acquisto non è andato a buon fine, il prodotto {prodotto.nome} è stato rimosso dalla piattaforma. Le arriverà un rimborso completo il prima possibile."
        )
        return HttpResponse(status=200)
    
    if annuncio.qta_magazzino < quantita:
        create_notification(
            recipient=user,
            title="Acquisto Annullato",
            message=f"Purtroppo l'acquisto non è andato a buon fine, le scorte del prodotto {prodotto.nome} in magazzino sono finite o inferiori alla sua richiesta. Le arriverà un rimborso completo il prima possibile."
        )
        stato = "annullato"
    else:
        annuncio.qta_magazzino = annuncio.qta_magazzino - quantita
        annuncio.save()
        stato = "da spedire"

    ordine = Ordine.objects.create(
        utente=user,
        prodotto=prodotto,
        quantita=quantita,
        invoice=invoice_obj.invoice_id,
        stato_consegna=stato
    )

    shipping = pu.get('shipping', {})
    address = shipping.get('address', {})
    if address:
        ordine.luogo_consegna = address
        ordine.save()
        invoice_obj.delete()
        create_notification(
            recipient=user,
            title="Acquisto Confermato!",
            message=f"L'acquisto di {prodotto.nome} è andato a buon fine!"
        )
        create_notification(
            recipient=annuncio.inserzionista,
            title="Un utente ha acquistato!",
            message=f"Un utente ha acquistato {ordine.quantita} unità di {ordine.prodotto.nome}!"
        )
    else:
        return HttpResponse(status=400)
    return HttpResponse(status=200)

@csrf_exempt
@require_POST
def paypal_coa(request):
    body = request.body

    if not verify_paypal_webhook(request, body):
        return HttpResponse(status=401)
    
    payload = json.loads(body)
    event_type = payload.get('event_type')
    resource = payload.get('resource', {})

    if event_type == 'CHECKOUT.ORDER.APPROVED':
        purchase_units = resource.get('purchase_units', [])
        if not purchase_units:
            return HttpResponse(status=400)

        pu = purchase_units[0]  # prendi il primo purchase unit
        invoice_id = pu.get('invoice_id')

        invoice_obj = None
        cart_obj = None

        try:
            invoice_obj = Invoice.objects.get(invoice_id=invoice_id)
        except Invoice.DoesNotExist:
            try:
                cart_obj = Cart.objects.get(invoice=invoice_id)
            except Cart.DoesNotExist:
                return HttpResponse(status=404)
        
        if invoice_obj:
            return invoice_validation(invoice_obj, pu)
        else:
            # Per ogni invoice associata al carrello, processa come sopra
            invoices = Invoice.objects.filter(cart=cart_obj)
            response = None
            for inv in invoices:
                response = invoice_validation(inv, pu)
            return response if response else HttpResponse(status=200)

    return HttpResponse(status=400)

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
            raise ValidationError('iban_form')
        
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
            raise ValidationError('iban_contr')

    def post(self, request):
        iban = request.POST.get('iban')
        
        try:
            self.validate_iban(iban)
            Iban.objects.update_or_create(utente=request.user,defaults={'iban':iban})
            # Restituisci una risposta di successo
        except ValidationError as e:
            error_message = e.messages[0] if e.messages else str(e)
            # Restituisci una risposta di errore con il messaggio
            return render(request, self.template_name, {'evento': error_message})
        return redirect(f'{reverse("sylvelius:profile_annunci")}?evento=iban_imp')

@require_POST
@login_required
def add_to_cart(request):
    annuncio, quantity, error_redirect = get_invoice_data(request)
    if error_redirect:
        return error_redirect
    
    carrello, created = Cart.objects.get_or_create(utente=request.user)
    if created:
        carrello.invoice = f'{uuid.uuid4()}' 
    carrello.save()
    create_invoice(request, annuncio, quantity, cart=carrello)
    
    return redirect(
        reverse("sylvelius:dettagli_annuncio", kwargs={"uuid": annuncio.uuid}) +  # type: ignore
        "?evento=carrello"
    )

class CarrelloPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin,TemplateView):
    template_name = "purchase/carrello.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if Cart.objects.filter(utente=self.request.user).exists(): #type:ignore
            context['cart'] = self.request.user.cart #type:ignore
        return context

class CheckoutPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin,TemplateView):
    template_name = "purchase/checkout.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if Cart.objects.filter(utente = self.request.user).exists():
            for invoice in self.request.user.cart.invoices.all():  #type:ignore
                try:
                    Annuncio.objects.get(prodotto=invoice.prodotto)
                except Annuncio.DoesNotExist:
                    # Elimina tutte le invoice con lo stesso prodotto
                    Invoice.objects.filter(prodotto=invoice.prodotto, cart=self.request.user.cart).delete() #type:ignore
            context['cart'] = self.request.user.cart  #type:ignore
            context['amount'] = self.request.user.cart.total #type:ignore
            context['paypal_client_id'] = settings.xxx
            context['invoice_id'] = self.request.user.cart.invoice #type:ignore
        return context
# non callable
def controlla_annuncio_e_quantita(invoice, incremento=1):
    try:
        annuncio = Annuncio.objects.get(prodotto=invoice.prodotto)
    except Annuncio.DoesNotExist:
        # Elimina tutte le invoice con lo stesso prodotto
        Invoice.objects.filter(prodotto=invoice.prodotto, user=invoice.user).delete()
        return redirect(
            reverse("purchase:carrello") +
            "?evento=articoli_inesistenti"
        ), None

    nuova_quantita = invoice.quantita + incremento
    if nuova_quantita > annuncio.qta_magazzino:
        # Imposta la quantità massima disponibile
        invoice.quantita = annuncio.qta_magazzino
        invoice.save()
        return redirect(
            reverse("purchase:carrello") +
            "?evento=troppi_articoli"
        ), annuncio

    return None, annuncio

@require_POST
@login_required
def aumenta_carrello(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    error_redirect, annuncio = controlla_annuncio_e_quantita(invoice, incremento=1)
    if error_redirect:
        return error_redirect

    invoice.quantita += 1
    invoice.save()
    return redirect(reverse("purchase:carrello"))

@require_POST
@login_required
def diminuisci_carrello(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    # Per diminuzione, non serve controllo magazzino, ma serve controllo esistenza annuncio
    error_redirect, annuncio = controlla_annuncio_e_quantita(invoice, incremento=-1)
    if error_redirect:
        return error_redirect

    if invoice.quantita > 1:
        invoice.quantita -= 1
        invoice.save()
    else:
        invoice.delete()
    return redirect(reverse("purchase:carrello"))

@require_POST
@login_required
def rimuovi_da_carrello(request, invoice_id):
    invoice = get_object_or_404(Invoice,invoice_id=invoice_id)
    invoice.delete()
    return redirect(reverse("purchase:carrello") + '?evento=rimosso')
