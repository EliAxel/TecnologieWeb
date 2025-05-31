# Django core
from PIL import Image
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse, HttpResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, CreateView
from django.db.models import Avg
from django.db.models.functions import Floor
from django.shortcuts import (
    render, 
    redirect, 
    get_object_or_404,
    resolve_url
)

# Project specific
from django.conf import settings
from .models import (
    Annuncio,
    CommentoAnnuncio,
    Creazione,
    ImmagineProdotto,
    Ordine,
    Tag,
    Prodotto,
    Invoice
)

# Other
import json
import uuid
import requests
from requests.auth import HTTPBasicAuth

# Create your views here.
class HomePageView(TemplateView):
    template_name = "sylvelius/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        annunci = Annuncio.objects.filter(is_published=True).order_by('-data_pubblicazione')

        paginator = Paginator(annunci, 21)

        try:
            page_number = int(self.request.GET.get('page', 1))
            if page_number < 1:
                page_number = 1
        except ValueError:
            page_number = 1

        page_obj = paginator.get_page(page_number)

        context['annunci'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        context['request'] = self.request  # Per usare request.GET nel template

        return context

class RegistrazionePageView(CreateView):
    form_class = UserCreationForm
    template_name = "sylvelius/register.html"
    def form_invalid(self, form):
        return HttpResponseRedirect(reverse('sylvelius:register') + '?auth=notok')
    
    def get_success_url(self):
        return reverse('sylvelius:home') + '?auth=ok'

class LoginPageView(LoginView):
    template_name = "sylvelius/login.html"

class LogoutPageView(LogoutView):
    next_page = reverse_lazy('sylvelius:home')

class CustomLoginRequiredMixin(LoginRequiredMixin):
    def get_login_url(self):
        login_url = super().get_login_url()
        return f"{resolve_url(login_url)}?auth=error"
    
class ProfiloPageView(CustomLoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile/profile.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        context['creazioni'] = Creazione.objects.filter(utente=utente).order_by('-data_creazione')
        context['ordini'] = Ordine.objects.filter(utente=utente).order_by('-data_ordine')

        # Trova tutti gli utenti che hanno fatto ordini su annunci creati dall'utente corrente
        # e per cui almeno un ordine è "in attesa"
        mie_creazioni = Creazione.objects.filter(utente=utente).values_list('annuncio_id', flat=True)
        prodotti_mie_creazioni = Annuncio.objects.filter(
            id__in=mie_creazioni
        ).values_list('prodotto_id', flat=True)

        ordini_clienti = (
            Ordine.objects
            .filter(prodotto_id__in=prodotti_mie_creazioni, stato_consegna='da spedire')
            .select_related('utente', 'prodotto')
        )

        clienti_dict = {}
        for ordine in ordini_clienti:
            cliente = ordine.utente
            if cliente not in clienti_dict:
                clienti_dict[cliente] = {
                    'username': cliente.username,
                    'ordini_da_rifornire': []
                }
            clienti_dict[cliente]['ordini_da_rifornire'].append(ordine)

        # Lista di oggetti utente con attributo aggiunto "ordini_da_rifornire"
        clienti = []
        for cliente, data in clienti_dict.items():
            cliente.ordini_da_rifornire = data['ordini_da_rifornire']
            clienti.append(cliente)

        context['clienti'] = clienti

        return context

class ProfiloEditPageView(CustomLoginRequiredMixin, View):
    template_name = "sylvelius/profile/profile_edit.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        return render(request, self.template_name, {'user': request.user})

    def post(self, request):
        user = request.user
        username = request.POST.get('username', user.username)
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        # Verifica la vecchia password
        if not user.check_password(old_password):
            return render(request, self.template_name, {'user': user})

        # Aggiorna username se cambiato
        if username and username != user.username:
            user.username = username

        # Gestione cambio password
        if new_password1 or new_password2:
            if new_password1 != new_password2:
                return render(request, self.template_name, {'user': user})
            if new_password1:
                user.set_password(new_password1)
                update_session_auth_hash(request, user)

        user.save()
        return redirect('sylvelius:profile')

class ProfiloDeletePageView(CustomLoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile/profile_delete.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

class AnnuncioDetailView(TemplateView):
    template_name = "sylvelius/annuncio/dettagli_annuncio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        annuncio_id = self.kwargs['pk']
        annuncio = get_object_or_404(Annuncio, id=annuncio_id, is_published=True)
        commenti = CommentoAnnuncio.objects.filter(
            annuncio=annuncio
        ).select_related('utente').order_by('-data_pubblicazione')

        ha_acquistato = False
        if user.is_authenticated:
            ha_acquistato = Ordine.objects.filter(
                utente=user,
                prodotto=annuncio.prodotto,
                stato_consegna='consegnato'
            ).exists()
        non_ha_commentato = True
        if user.is_authenticated:
            non_ha_commentato = not CommentoAnnuncio.objects.filter(
                annuncio=annuncio,
                utente=user
            ).exists()

        context['get_commento'] = CommentoAnnuncio.objects.filter(
            annuncio=annuncio,
            utente=user
        ).first() if user.is_authenticated else None

        context['non_ha_commentato'] = non_ha_commentato
        context['ha_acquistato'] = ha_acquistato
        context['annuncio'] = annuncio
        context['commenti'] = commenti
        return context
    
class ProfiloOrdiniPageView(CustomLoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile/profile_ordini.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        ordini_list = Ordine.objects.filter(utente=utente).order_by('-data_ordine')
        
        paginator = Paginator(ordini_list, 20)  # 20 ordini per pagina
        
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['ordini'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        context['request'] = self.request

        
        return context
    
class ProfiloCreazioniPageView(CustomLoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile/profile_creazioni.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        creazioni_list = Creazione.objects.filter(utente=utente).order_by('-data_creazione')
        
        paginator = Paginator(creazioni_list, 20)  # 20 creazioni per pagina
        
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['creazioni'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        context['request'] = self.request

        return context

class ProfiloCreaCreazionePageView(CustomLoginRequiredMixin, View):
    template_name = "sylvelius/annuncio/crea_annuncio.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        error = {'notok': '1'}

        nome = request.POST.get('nome')
        descrizione = request.POST.get('descrizione', '')
        descrizione_breve = request.POST.get('descrizione_breve')
        prezzo = request.POST.get('prezzo')
        tag_string = request.POST.get('tags', '')  # è una stringa unica!
        immagini = request.FILES.getlist('immagini')
        qta_magazzino = request.POST.get('qta_magazzino', 1)
        condizione = request.POST.get('condizione', 'nuovo')

        if condizione not in ['nuovo', 'usato']:
            return render(request, self.template_name, error)

        # Validazione base
        if not nome.strip('') or not descrizione_breve.strip('') or not prezzo:
            return render(request, self.template_name, error)
        
        if len(nome) > 100 or len(descrizione_breve) > 255 or len(descrizione) > 3000:
            return render(request, self.template_name, error)
        
        try:
            prezzo = float(prezzo)
        except ValueError:
            return render(request, self.template_name, error)
        
        if prezzo < 0 or prezzo > 1000000:
            return render(request, self.template_name, error)
        
        try:
            qta_magazzino = int(qta_magazzino)
        except ValueError:
            return render(request, self.template_name, error)
        if qta_magazzino < 1:
            return render(request, self.template_name, error)

        prodotto=Prodotto.objects.create(
                nome=nome,
                descrizione_breve=descrizione_breve,
                descrizione=descrizione,
                prezzo=prezzo,
                condizione=condizione
            )
        # Creazione dell'annuncio
        annuncio = Annuncio.objects.create(
            prodotto=prodotto,
            data_pubblicazione=None,
            qta_magazzino=qta_magazzino,
            is_published=True
        )

        # Gestione dei tag (split manuale)
        tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
        tag_instances = []
        for nome in tag_names:
            tag, _ = Tag.objects.get_or_create(nome=nome)
            tag_instances.append(tag)
        annuncio.prodotto.tags.set(tag_instances)

        # Salva immagini
        for img in immagini:
            try:
                Image.open(img).verify()  # Verifica se è immagine valida
            except Exception:
                return render(request, self.template_name, error)
            ImmagineProdotto.objects.create(prodotto=prodotto, immagine=img)

        # Crea la creazione associata all'utente
        Creazione.objects.create(
            utente=request.user,
            annuncio=annuncio
        )

        return redirect('sylvelius:home')

class RicercaAnnunciView(TemplateView):
    template_name = "sylvelius/ricerca.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        categoria_str = self.request.GET.get('categoria', '').strip()
        prezzo_min = self.request.GET.get('prezzo_min')
        prezzo_max = self.request.GET.get('prezzo_max')
        sort_order = self.request.GET.get('sort', 'data-desc')
        condizione = self.request.GET.get('condition')
        rating = self.request.GET.get('search_by_rating')

        annunci = Annuncio.objects.filter(is_published=True)

        if query:
            annunci = annunci.filter(
                Q(prodotto__nome__icontains=query) |
                Q(prodotto__descrizione_breve__icontains=query) |
                Q(prodotto__tags__nome__icontains=query)
            )

        if categoria_str:
            tag_list = [tag.strip() for tag in categoria_str.split(',') if tag.strip()]
            if tag_list:
                for tag in tag_list:
                    annunci = annunci.filter(prodotto__tags__nome=tag)
        

        if condizione == 'cond-new':
            annunci = annunci.filter(prodotto__condizione='nuovo')
        elif condizione == 'cond-used':
            annunci = annunci.filter(prodotto__condizione='usato')
        elif condizione == 'all':
            pass
            
        if rating:
            try:
                rating_value = int(rating)
                if 0 <= rating_value <= 5:
                    # Supponiamo che 'rating_value' sia il valore dell'intervallo desiderato (da 0 a 4)
                    annunci = Annuncio.objects.annotate(
                        rating_medio_calc=Avg('commenti__rating'),
                        rating_range=Floor(Avg('commenti__rating'))
                    ).filter(
                        rating_range=rating_value
                    ).exclude(
                        rating_medio_calc__isnull=True
                    )

                else:
                    raise ValueError("Rating fuori range")
            except (ValueError, TypeError):
                if rating == 'all':
                    pass
                elif rating == 'none':
                    # Se 'none', escludi gli annunci con commenti
                    annunci = annunci.exclude(commenti__isnull=False)
                elif rating == 'starred':
                    annunci = annunci.exclude(commenti__isnull=True)
                else:
                    # Se il rating non è valido, non filtrare
                    pass

        if prezzo_min:
            try:
                annunci = annunci.filter(prodotto__prezzo__gte=float(prezzo_min))
            except ValueError:
                pass

        if prezzo_max:
            try:
                annunci = annunci.filter(prodotto__prezzo__lte=float(prezzo_max))
            except ValueError:
                pass

        if sort_order == "data-desc":
            annunci = annunci.order_by('-data_pubblicazione')
        elif sort_order == "data-asc":
            annunci = annunci.order_by('data_pubblicazione')
        elif sort_order == "prezzo-asc":
            annunci = annunci.order_by('prodotto__prezzo')
        elif sort_order == "prezzo-desc":
            annunci = annunci.order_by('-prodotto__prezzo')

        annunci = annunci.distinct()

        paginator = Paginator(annunci, 50)
        page_number = self.request.GET.get('page', 1)
        try:
            page_number = int(page_number)
            if page_number < 1:
                page_number = 1
        except ValueError:
            page_number = 1

        page_obj = paginator.get_page(page_number)

        context['annunci'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        context['request'] = self.request

        return context

@login_required
def toggle_pubblicazione(request, id):
    # Trova la creazione dell'utente (che contiene l'annuncio)
    creazione = get_object_or_404(Creazione, annuncio__id=id, utente=request.user)
    annuncio = creazione.annuncio
    if request.method == "POST":
        annuncio.is_published = not annuncio.is_published
        annuncio.save()
    page = request.GET.get('page', 1)
    return redirect(f'{reverse_lazy("sylvelius:profile_creazioni")}?page={page}')

@login_required
def delete_pubblicazione(request, id):
    creazione = get_object_or_404(Creazione, id=id, utente=request.user)
    annuncio = creazione.annuncio
    
    if request.method == "POST":
        annuncio.delete()
    
    page = request.POST.get('page', 1)
    return redirect(f'{reverse_lazy("sylvelius:profile_creazioni")}?page={page}')


@require_POST
@login_required
def check_old_password(request):
    data = json.loads(request.body)
    old_password = data.get('old_password', '')

    if request.user.check_password(old_password):
        return JsonResponse({'valid': True})
    else:
        return JsonResponse({'valid': False})

@require_POST
def check_username_exists(request):
    data = json.loads(request.body)
    username = data.get("username", "").strip()
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({"exists": exists})

@require_POST
def check_login_credentials(request):
    data = json.loads(request.body)
    username = data.get("username")
    password = data.get("password")
    try:
        user = User.objects.get(username=username)
        exists = True
        valid_password = user.check_password(password)
    except User.DoesNotExist:
        exists = False
        valid_password = False

    return JsonResponse({
        "exists": exists,
        "valid_password": valid_password,
    })

@require_POST
@login_required
def aggiungi_commento(request, annuncio_id):
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, is_published=True)
    utente = request.user

    testo = request.POST.get('testo', '').strip()
    rating = request.POST.get('rating')

    # Validazione
    if not testo or not rating.isdigit() or int(rating) < 0 or int(rating) > 5 or len(testo) > 1000:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "error", "message": "Dati non validi"}, status=400)
        return redirect(reverse('sylvelius:dettagli_annuncio', args=[annuncio_id]) + '?comment=notok')

    # Salva il commento
    commento = CommentoAnnuncio.objects.create(
        annuncio=annuncio,
        utente=utente,
        testo=testo,
        rating=int(rating)
    )
    commento.save()

    # Risposta JSON se è una chiamata AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "success"})

    # Altrimenti redirect classico
    return redirect(reverse('sylvelius:dettagli_annuncio', args=[annuncio_id]))

@login_required
def modifica_commento(request, commento_id):
    commento = get_object_or_404(CommentoAnnuncio, id=commento_id, utente=request.user)

    if request.method == "POST":
        testo = request.POST.get('testo', '').strip()
        rating = request.POST.get('rating')

        # Validazione
        if not testo or not rating.isdigit() or int(rating) < 0 or int(rating) > 5 or len(testo) > 1000:
            return JsonResponse({"status": "error", "message": "Dati non validi"}, status=400)

        # Aggiorna il commento
        commento.testo = testo
        commento.rating = int(rating)
        commento.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "success"})

    return render(request, "sylvelius/annuncio/modifica_commento.html", {"commento": commento})

@login_required
def elimina_commento(request, commento_id):
    if request.method == "DELETE":
        commento = get_object_or_404(CommentoAnnuncio, id=commento_id, utente=request.user)
        commento.delete()
        return JsonResponse({"status": "success"})
    else:
        return HttpResponseBadRequest("Metodo non consentito")

@require_POST
@login_required
def fake_purchase(request):    
    amount = request.POST.get("amount", "0.00")
    item_name = request.POST.get("item_name", "Prodotto sconosciuto")
    product_id = request.POST.get("product_id", "")
    quantity = request.POST.get("quantity", "1")
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
        return render(request, "sylvelius/payment/payment_process.html", {
            "amount": amount,
            "item_name": item_name,
            "invoice_id": invoice_id,
            "quantity": quantity,
            "paypal_client_id": settings.xxx,
        })
    return HttpResponseBadRequest("Metodo non supportato")

def payment_done(request):
    return render(request, 'sylvelius/payment/payment_done.html')

def payment_cancelled(request):
    return render(request, 'sylvelius/payment/payment_cancelled.html')

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
                invoice_id=invoice,
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

            ordine = Ordine.objects.filter(invoice_id=invoice, prodotto=prodotto).first()

            if ordine:
                shipping = pu.get('shipping', {})
                address = shipping.get('address', {})
                ordine.luogo_consegna = address
                ordine.save()
                del invoice_obj
            else:
                return HttpResponse(status=102)

            return HttpResponse(status=200)
        return HttpResponse(status=400)

    except Exception as e:
        return HttpResponse(status=500)
