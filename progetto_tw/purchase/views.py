from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from sylvelius.models import Ordine, Annuncio
from sylvelius.views import create_notification
from .models import Invoice, Iban, Cart
from progetto_tw.mixins import CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin

import json
import re
import requests
import uuid
from decimal import Decimal
from requests.auth import HTTPBasicAuth

# non callable
def validate_quantity(quantity, annuncio):
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
# non callable
def create_invoice(request, annuncio, quantity, cart=None):
    invoice_obj, created = Invoice.objects.update_or_create(
        utente=request.user,
        prodotto=annuncio.prodotto,
        cart=cart,
        defaults={
            "quantita": quantity,
            "uuid": str(uuid.uuid4()) if not Invoice.objects.filter(utente=request.user, prodotto=annuncio.prodotto, cart=cart).exists() else Invoice.objects.get(utente=request.user, prodotto=annuncio.prodotto, cart=cart).uuid
        }
    )
    return invoice_obj
# non callable
def get_invoice_data(request):
    annuncio_id = request.POST.get("annuncio_id")
    if not annuncio_id:
        annuncio_id = request.GET.get("annuncio_id")
    annuncio = get_object_or_404(Annuncio, uuid=annuncio_id, is_published=True)
    quantity = request.POST.get("quantita")
    if not quantity:
        quantity = request.GET.get("quantita")
    error_redirect = validate_quantity(quantity, annuncio)
    if error_redirect:
        return None, None, error_redirect
    
    return annuncio, int(quantity), None
# non callable
def create_cart_get_invoice(request):
    annuncio, quantity, error_redirect = get_invoice_data(request)
    if error_redirect:
        return error_redirect, None
    
    carrello, created = Cart.objects.get_or_create(utente=request.user)
    if created:
        carrello.uuid = f'{uuid.uuid4()}' 
        carrello.save()
    
    return None, create_invoice(request, annuncio, quantity, cart=carrello)

class PurchasePageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, View):
    template_name = "purchase/payment_process.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        err, invoice = create_cart_get_invoice(request)
        if err:
            return err
        product = invoice.prodotto# type: ignore
        context = {
            "amount": product.prezzo * Decimal(invoice.quantita), # type: ignore
            "item_name": product.nome, # type: ignore
            "uuid": invoice.uuid, # type: ignore
            "quantity": invoice.quantita, # type: ignore
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
    PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  
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
    user = invoice_obj.utente
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
        invoice=invoice_obj.uuid,
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

        pu = purchase_units[0]
        uuid = pu.get('invoice_id')

        invoice_obj = None
        cart_obj = None

        try:
            invoice_obj = Invoice.objects.get(uuid=uuid)
        except Invoice.DoesNotExist:
            try:
                cart_obj = Cart.objects.get(uuid=uuid)
            except Cart.DoesNotExist:
                return HttpResponse(status=404)
        
        if invoice_obj:
            return invoice_validation(invoice_obj, pu)
        else:
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
        iban = iban.replace(' ', '').upper()
        
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$', iban):
            raise ValidationError('iban_form')
        
        rearranged = iban[4:] + iban[:4]
        
        digits = []
        for char in rearranged:
            if char.isdigit():
                digits.append(char)
            else:
                digits.append(str(10 + ord(char) - ord('A')))
        
        numeric_iban = int(''.join(digits))
        if numeric_iban % 97 != 1:
            raise ValidationError('iban_contr')

    def post(self, request):
        iban = request.POST.get('iban')
        
        try:
            self.validate_iban(iban)
            Iban.objects.update_or_create(utente=request.user,defaults={'iban':iban})
        except ValidationError as e:
            error_message = e.messages[0] if e.messages else str(e)
            return render(request, self.template_name, {'evento': error_message})
        return redirect(f'{reverse("sylvelius:profile_annunci")}?evento=iban_imp')

@require_POST
@login_required 
def add_to_cart(request):
    err, invoice = create_cart_get_invoice(request)
    if err:
        return err
    
    return redirect(
        reverse("sylvelius:dettagli_annuncio", kwargs={"uuid": invoice.prodotto.annunci.uuid}) + #type: ignore
        "?evento=carrello"
    )
# non callable
def controlla_annuncio_e_quantita(invoice, incremento=1):
    try:
        annuncio = Annuncio.objects.get(prodotto=invoice.prodotto)
    except Annuncio.DoesNotExist:
        Invoice.objects.filter(prodotto=invoice.prodotto, utente=invoice.utente).delete()
        return redirect(
            reverse("purchase:carrello") +
            "?evento=articoli_inesistenti"
        )

    nuova_quantita = invoice.quantita + incremento
    if nuova_quantita > annuncio.qta_magazzino:
        invoice.quantita = annuncio.qta_magazzino
        invoice.save()
        return redirect(
            reverse("purchase:carrello") +
            "?evento=troppi_articoli"
        )

    return None
# non callable
def carrello_or_checkout_integrity(request):
    redirects = redirect(
        reverse("purchase:carrello") +
        "?evento=articoli_inesistenti"
    )
    deleted = False 
    for invoice in request.user.cart.invoices.all():  #type:ignore
        try:
            Annuncio.objects.get(prodotto=invoice.prodotto,inserzionista__is_active=True,is_published=True)
        except Annuncio.DoesNotExist:
            inv = Invoice.objects.filter(prodotto=invoice.prodotto, cart=request.user.cart)#type:ignore
            for invc in inv:
                create_notification(recipient=invc.utente, title='Articolo nel carrello rimosso', 
                                    message='L\'annuncio relativo all\'articolo è stato rimosso/nascosto o l\'inserzionista è stato bandito.')
            inv.delete()
            deleted = True
        error_redirect = controlla_annuncio_e_quantita(invoice, incremento=0)
        if error_redirect:
            return error_redirect
    return redirects if deleted else None

class CarrelloPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin,View):
    template_name = "purchase/carrello.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        context = {}
        if Cart.objects.filter(utente=request.user).exists(): #type:ignore
            err = carrello_or_checkout_integrity(request)
            if err:
                return err

            context['cart'] = request.user.cart #type:ignore
        return render(request, self.template_name, context)

class CheckoutPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin,View):
    template_name = "purchase/checkout.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self,request):
        context = {}
        if Cart.objects.filter(utente = request.user).exists():
            err = carrello_or_checkout_integrity(request)
            if err:
                return err
            
            context['cart'] = request.user.cart  #type:ignore
            context['amount'] = request.user.cart.total #type:ignore
            context['paypal_client_id'] = settings.xxx
            context['uuid'] = request.user.cart.uuid #type:ignore
        return render(request, self.template_name, context)

@require_POST
@login_required
def aumenta_carrello(request, uuid):
    invoice = get_object_or_404(Invoice, uuid=uuid, utente=request.user)
    error_redirect = controlla_annuncio_e_quantita(invoice, incremento=1)
    if error_redirect:
        return error_redirect

    invoice.quantita += 1
    invoice.save()
    return redirect(reverse("purchase:carrello"))

@require_POST
@login_required
def diminuisci_carrello(request, uuid):
    invoice = get_object_or_404(Invoice, uuid=uuid, utente=request.user)
    error_redirect = controlla_annuncio_e_quantita(invoice, incremento=-1)
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
def rimuovi_da_carrello(request, uuid):
    invoice = get_object_or_404(Invoice,uuid=uuid, utente=request.user)
    invoice.delete()
    return redirect(reverse("purchase:carrello") + '?evento=rimosso')

@require_POST
@login_required
def rimuovi_carrello(request, cart_id):
    cart = get_object_or_404(Cart,uuid=cart_id,utente=request.user)
    for invoice in cart.invoices.all():  # type: ignore
        invoice.delete()
    
    return redirect(reverse("purchase:carrello") + '?evento=rimossi')