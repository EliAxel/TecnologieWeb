# Django core
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, CreateView
from django.db.models import Avg
from django.db.models.functions import Floor
from django.shortcuts import (
    render, 
    redirect, 
    get_object_or_404
)

from purchase.models import Iban
# Project specific
from .forms import CustomUserCreationForm
from progetto_tw.mixins import CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin
from .models import (
    Annuncio,
    CommentoAnnuncio,
    ImmagineProdotto,
    Ordine,
    Tag,
    Prodotto,
    Notification
)
from progetto_tw.constants import (
    MAX_UNAME_CHARS,
    MAX_PWD_CHARS,
    MAX_TAGS_CHARS,
    MAX_TAGS_N_PER_PROD,
    MAX_IMGS_PER_ANNU_VALUE,
    MAX_PROD_NOME_CHARS,
    MAX_PROD_DESC_BR_CHARS,
    MAX_PROD_DESC_CHARS,
    MIN_PROD_PREZZO_VALUE,
    MAX_PROD_PREZZO_VALUE,
    MAX_ANNU_QTA_MAGAZZINO_VALUE,
    MAX_COMMNT_TESTO_CHARS,
    MIN_COMMNT_RATING_VALUE,
    MAX_COMMNT_RATING_VALUE,
    MAX_PAGINATOR_HOME_VALUE,
    MAX_PAGINATOR_ORDINI_VALUE,
    MAX_PAGINATOR_ANNUNCI_VALUE,
    MAX_PAGINATOR_RICERCA_VALUE,
    MAX_PAGINATOR_BANNED_USERS_VALUE,
    MIN_CREA_ANNUNCIO_QTA_VALUE,
    ALIQUOTE_LIST_VALS,
    PROD_CONDIZIONE_CHOICES_ID
)
# Other
import json
import uuid
from PIL import Image
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Create your views here.
def send_notification(user_id=None,title="", message="", global_notification=False):
    channel_layer = get_channel_layer()

    if global_notification:
        async_to_sync(channel_layer.group_send)( #type: ignore
            "global", {"type": "send_notification", "title":title, "message": message}
        )
    elif user_id:
        async_to_sync(channel_layer.group_send)( #type: ignore
            f"user_{user_id}", {"type": "send_notification", "title":title, "message": message}
        )

@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return JsonResponse({'status': 'ok'})

def create_notification(recipient=None, title="", message="", is_global=False, sender=None):
    # Salva nel database
    notifica = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        is_global=is_global,
        read=False
    )
    
    # Invia via WebSocket
    send_notification(
        user_id=recipient.id if recipient else None,
        title=title,
        message=message,
        global_notification=is_global
    )
    
    return notifica

class HomePageView(TemplateView):
    template_name = "sylvelius/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        annunci = Annuncio.objects.filter(is_published=True).order_by('-data_pubblicazione')

        paginator = Paginator(annunci, MAX_PAGINATOR_HOME_VALUE)

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
    form_class = CustomUserCreationForm
    template_name = "sylvelius/register.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        return response
    
    def form_invalid(self, form):
        return HttpResponseRedirect(reverse('sylvelius:register') + '?auth=notok')
    
    def get_success_url(self):
            return reverse('sylvelius:login') + '?reg=ok'

class LoginPageView(LoginView):
    template_name = "sylvelius/login.html"

class LogoutPageView(LogoutView):
    def get_success_url(self):
        return reverse('sylvelius:home') + '?evento=logout'
    
class ProfiloPageView(CustomLoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile/profile.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.groups.filter(name='moderatori').exists():
            user_without_is_active_list = User.objects.filter(is_active=False).order_by('username')
            
            paginator = Paginator(user_without_is_active_list, MAX_PAGINATOR_BANNED_USERS_VALUE)  # 10 utenti per pagina
        
            page_number = self.request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            context['user_without_is_active'] = page_obj.object_list
            context['page'] = page_obj.number
            context['has_next'] = page_obj.has_next()
            context['has_previous'] = page_obj.has_previous()
            context['request'] = self.request
        else:
            utente = self.request.user
            context['user'] = utente
            context['annunci'] = Annuncio.objects.filter(inserzionista=utente).order_by('-data_pubblicazione')
            context['ordini'] = Ordine.objects.filter(utente=utente).order_by('-data_ordine')
            # Trova tutti gli utenti che hanno fatto ordini su annunci creati dall'utente corrente
            # e per cui almeno un ordine è "in attesa"
            miei_annunci = Annuncio.objects.filter(inserzionista=utente).values_list('id', flat=True)
            prodotti_miei_annunci = Annuncio.objects.filter(
                id__in=miei_annunci
            ).values_list('prodotto_id', flat=True)

            ordini_clienti = (
                Ordine.objects
                .filter(prodotto_id__in=prodotti_miei_annunci, stato_consegna='da spedire')
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
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username').strip()
        old_password = request.POST.get('old_password').strip()
        new_password1 = request.POST.get('new_password1').strip()
        new_password2 = request.POST.get('new_password2').strip()

        if len(username) > MAX_UNAME_CHARS:
            return render(request, self.template_name, {'usr': 'bad'})
        if len(new_password1) > MAX_PWD_CHARS:
            return render(request, self.template_name, {'pwd': 'bad'})
        password_change_form_valid = True
        if new_password1 and new_password2:
            password_change_form=PasswordChangeForm(data={
                'old_password': old_password,
                'new_password1': new_password1,
                'new_password2': new_password2
            },user=request.user)
            password_change_form_valid = password_change_form.is_valid()
            if password_change_form_valid: password_change_form.save()

        if username != request.user.username:
            request.user.username = username
            request.user.save()

        if password_change_form_valid:
            update_session_auth_hash(request, request.user)
            return redirect(f'{reverse("sylvelius:profile")}?evento=profile_edit')
        else:
            return render(request, self.template_name, {'pwd': 'bad'})

class ProfiloDeletePageView(CustomLoginRequiredMixin, View):
    login_url = reverse_lazy('sylvelius:login')
    template_name = "sylvelius/profile/profile_delete.html"

    def get(self, request):
        context = {
            'user': request.user,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        user = request.user
        if(Ordine.objects.filter(utente=user,stato_consegna="spedito").exists()):
            return render(request, self.template_name,{"err":"ship"})
        if(Ordine.objects.filter(
            prodotto__annunci__inserzionista=user,
            stato_consegna='spedito'
            ).exists()):
            return render(request, self.template_name,{"err":"shipd"})
        
        Ordine.objects.filter(utente=user,stato_consegna="da spedire").update(
            stato_consegna='annullato'
        )
        Ordine.objects.filter(
            prodotto__annunci__inserzionista=user,
            stato_consegna='da spedire'
            ).update(stato_consegna='annullato')

        Annuncio.objects.filter(inserzionista=user).delete()
        Iban.objects.filter(utente=request.user).delete()
        logout(request)  # logout PRIMA di eliminare l'utente per evitare problemi
        user.delete()    # elimina l'utente
        # 2. Reindirizza a una pagina di successo (es: home page)
        return redirect('sylvelius:home')

class AnnuncioDetailView(TemplateView):
    template_name = "sylvelius/annuncio/dettagli_annuncio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        annuncio_uuid = self.kwargs['uuid']
        annuncio = get_object_or_404(Annuncio, uuid=annuncio_uuid, is_published=True)
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
    
class ProfiloOrdiniPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, TemplateView):
    template_name = "sylvelius/profile/profile_ordini.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        ordini_list = Ordine.objects.filter(utente=utente).order_by('-data_ordine')
        
        paginator = Paginator(ordini_list, MAX_PAGINATOR_ORDINI_VALUE)  # 20 ordini per pagina
        
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['ordini'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        context['request'] = self.request

        return context
    
class ProfiloAnnunciPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, TemplateView):
    template_name = "sylvelius/profile/profile_annunci.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        annunci_list = Annuncio.objects.filter(inserzionista=utente).order_by('-data_pubblicazione')
        
        paginator = Paginator(annunci_list, MAX_PAGINATOR_ANNUNCI_VALUE)  # 20 creazioni per pagina
        
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['annunci'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        context['request'] = self.request

        return context

class ProfiloCreaAnnuncioPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, View):
    template_name = "sylvelius/annuncio/crea_annuncio.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        if request.GET.get('annuncio_id'):
            ann_id = get_object_or_404(Annuncio,id=request.GET.get('annuncio_id'), inserzionista=request.user)
            context = {}
            context['annuncio_mod'] = request.GET.get('annuncio_id')
            context['titolo_mod'] = ann_id.prodotto.nome
            context['desc_br_mod'] = ann_id.prodotto.descrizione_breve
            context['desc_mod'] = ann_id.prodotto.descrizione
            context['prezzo_mod'] = ann_id.prodotto.prezzo
            context['iva_mod'] = ann_id.prodotto.iva
            context['qta_mod'] = ann_id.qta_magazzino
            context['cond_mod'] = ann_id.prodotto.condizione
            context['tags_mod'] = [tag.nome for tag in ann_id.prodotto.tags.all()]
            
            return render(request, self.template_name,context)
        else:
            return render(request, self.template_name)

    def post(self, request):
        annuncio_id = request.POST.get('annuncio_mod')
        nome = request.POST.get('nome').strip()
        descrizione = request.POST.get('descrizione', '')
        descrizione_breve = request.POST.get('descrizione_breve').strip()
        prezzo = request.POST.get('prezzo')
        iva = request.POST.get('iva')
        tag_string = request.POST.get('tags', '')  # è una stringa unica!
        immagini = request.FILES.getlist('immagini')
        qta_magazzino = request.POST.get('qta_magazzino', MIN_CREA_ANNUNCIO_QTA_VALUE)
        condizione = request.POST.get('condizione', 'nuovo')
        annuncio = None
        prodotto = None
        annuncio_mod = None
        if annuncio_id:
            annuncio_mod = get_object_or_404(Annuncio,id=annuncio_id,inserzionista=request.user)

        if condizione not in PROD_CONDIZIONE_CHOICES_ID:
            return render(request, self.template_name, {'notok': 'cond'})

        # Validazione base
        if not nome or not descrizione_breve or not prezzo:
            return render(request, self.template_name, {'notok': 'noval'})
        
        if (len(nome) > MAX_PROD_NOME_CHARS or
            len(descrizione_breve) > MAX_PROD_DESC_BR_CHARS or
            len(descrizione) > MAX_PROD_DESC_CHARS):
            return render(request, self.template_name, {'notok': 'lentxt'})
        
        try:
            prezzo = float(prezzo)
        except ValueError:
            return render(request, self.template_name, {'notok': 'prerr'})
        
        if prezzo < MIN_PROD_PREZZO_VALUE or prezzo > MAX_PROD_PREZZO_VALUE:
            return render(request, self.template_name, {'notok': 'price'})
        
        if iva not in ALIQUOTE_LIST_VALS:
            return render(request, self.template_name, {'notok': 'cond'})

        try:
            qta_magazzino = int(qta_magazzino)
        except ValueError:
            return render(request, self.template_name, {'notok': 'qtaerr'})
        if qta_magazzino < MIN_CREA_ANNUNCIO_QTA_VALUE or qta_magazzino > MAX_ANNU_QTA_MAGAZZINO_VALUE:
            return render(request, self.template_name, {'notok': 'qta'})
        
         # Gestione dei tag (split manuale)
        tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
        if(len(tag_names)>MAX_TAGS_N_PER_PROD):
            return render(request, self.template_name, {'notok': 'tagn'})
        
        tag_instances = []

        for nome in tag_names:
            if (len(nome) > MAX_TAGS_CHARS):
                return render(request, self.template_name, {'notok': 'tagchar'})
        
        # Salva immagini
        if(len(immagini) > MAX_IMGS_PER_ANNU_VALUE):
            return render(request, self.template_name, {'notok': 'imgn'})
        
        for img in immagini:
            try:
                Image.open(img).verify()  # Verifica se è immagine valida
            except Exception:
                return render(request, self.template_name, {'notok': 'imgtype'})

        if annuncio_mod:
            prodotto = Prodotto.objects.get(id=annuncio_mod.prodotto.id)  # type:ignore
            prodotto.nome = nome
            prodotto.descrizione_breve = descrizione_breve
            prodotto.descrizione = descrizione
            prodotto.prezzo = prezzo #type:ignore
            prodotto.condizione = condizione
            prodotto.iva = int(iva)
            prodotto.save()
        else:
            prodotto=Prodotto.objects.create(
                nome=nome,
                descrizione_breve=descrizione_breve,
                descrizione=descrizione,
                prezzo=prezzo,
                condizione=condizione,
                iva=int(iva)
            )
        # Creazione dell'annuncio
        if annuncio_mod:
            # Approccio alternativo che restituisce l'oggetto aggiornato
            annuncio = Annuncio.objects.get(id=annuncio_mod.id)  # type:ignore
            annuncio.uuid = annuncio_mod.uuid
            annuncio.inserzionista = request.user
            annuncio.prodotto = prodotto
            annuncio.data_pubblicazione = annuncio_mod.data_pubblicazione
            annuncio.qta_magazzino = qta_magazzino
            annuncio.is_published = annuncio_mod.is_published
            annuncio.save()
        else:
            annuncio = Annuncio.objects.create(
                uuid=uuid.uuid4(),
                inserzionista=request.user,
                prodotto=prodotto,
                data_pubblicazione=None,
                qta_magazzino=qta_magazzino,
                is_published=True
            )
            
        for nome in tag_names:
            tag, _ = Tag.objects.get_or_create(nome=nome)
            tag_instances.append(tag)
            
        annuncio.prodotto.tags.set(tag_instances) 

        # Salva immagini
        
        if len(immagini) > 0 and annuncio_mod:
            ImmagineProdotto.objects.filter(prodotto=prodotto).delete()

        for img in immagini:
            ImmagineProdotto.objects.create(prodotto=prodotto, immagine=img)

        page = request.GET.get('page', 1)
        
        if annuncio_id:
            return redirect(f'{reverse("sylvelius:profile_annunci")}?page={page}&evento=mod_annuncio')
        return redirect(f'{reverse("sylvelius:home")}?evento=crea_annuncio')

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
        

        if condizione in PROD_CONDIZIONE_CHOICES_ID:
            annunci = annunci.filter(prodotto__condizione=condizione)
        # Se condizione == 'all' o non valida, non filtrare
            
        if rating:
            try:
                rating_value = int(rating)
                if MIN_COMMNT_RATING_VALUE <= rating_value <= MAX_COMMNT_RATING_VALUE:
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

        paginator = Paginator(annunci, MAX_PAGINATOR_RICERCA_VALUE)
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

@require_POST
@login_required
def toggle_pubblicazione(request, id):
    # Trova la creazion dell'utente (che contiene l'annuncio)
    annuncio = get_object_or_404(Annuncio, id=id, inserzionista=request.user)
    annuncio.is_published = not annuncio.is_published
    annuncio.save()
    page = request.GET.get('page', 1)

    return redirect(f'{reverse("sylvelius:profile_annunci")}?page={page}&evento=nascondi')

@require_POST
@login_required
def delete_pubblicazione(request, id):
    if request.user.groups.filter(name='moderatori').exists():
        annuncio = get_object_or_404(Annuncio, id=id)
        annuncio.delete()  
        return redirect(f'{reverse("sylvelius:home")}?evento=elimina_pub')
    else:
        annuncio = get_object_or_404(Annuncio, id=id, inserzionista=request.user)
        annuncio.delete()  
        page = request.POST.get('page', 1)
        return redirect(f'{reverse("sylvelius:profile_annunci")}?page={page}&evento=elimina')

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
        is_active = user.is_active
    except User.DoesNotExist:
        exists = False
        valid_password = False
        is_active = False

    return JsonResponse({
        "exists": exists,
        "valid_password": valid_password,
        "is_active": is_active
    })

@require_POST
@login_required
def aggiungi_commento(request, annuncio_id):
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, is_published=True)
    utente = request.user

    testo = request.POST.get('testo', '').strip()
    rating = request.POST.get('rating')

    # Validazione
    if (not testo or
        not rating.isdigit() or
        int(rating) < MIN_COMMNT_RATING_VALUE or
        int(rating) > MAX_COMMNT_RATING_VALUE or
        len(testo) > MAX_COMMNT_TESTO_CHARS):
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

@require_POST
@login_required
def modifica_commento(request, commento_id):
    commento = get_object_or_404(CommentoAnnuncio, id=commento_id, utente=request.user)

    testo = request.POST.get('testo', '').strip()
    rating = request.POST.get('rating')

    # Validazione
    if (not testo or
        not rating.isdigit() or
        int(rating) < MIN_COMMNT_RATING_VALUE or
        int(rating) > MAX_COMMNT_RATING_VALUE or
        len(testo) > MAX_COMMNT_TESTO_CHARS):
        return JsonResponse({"status": "error", "message": "Dati non validi"}, status=400)

    # Aggiorna il commento
    commento.testo = testo
    commento.rating = int(rating)
    commento.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "success"})

    return render(request, "sylvelius/annuncio/dettagli_annuncio.html", {"commento": commento})

@require_POST
@login_required
def elimina_commento(request, commento_id):
    if request.user.groups.filter(name='moderatori').exists():
        commento = get_object_or_404(CommentoAnnuncio, id=commento_id)
        commento.delete()
    else:
        commento = get_object_or_404(CommentoAnnuncio, id=commento_id, utente=request.user)
        commento.delete()
    return JsonResponse({"status": "success"})

@require_POST
@login_required
def espelli_utente(request, is_active, user_id):
    if request.user.groups.filter(name='moderatori').exists():
        user = get_object_or_404(User, id=user_id)
        user.is_active = False if is_active=='ban' else True
        user.save()
        return redirect(f'{reverse("sylvelius:profile")}?evento=elimina_ut')
    else:
        return HttpResponseForbidden()
    
@require_POST
@login_required
def formatta_utente(request, user_id):
    if request.user.groups.filter(name='moderatori').exists():
        user = get_object_or_404(User, id=user_id)
        if(not user.is_active):
            Ordine.objects.filter(
                Q(prodotto__annunci__inserzionista=user) &
                Q(stato_consegna='da spedire')
            ).update(stato_consegna='annullato')
            Ordine.objects.filter(utente=user.id).delete()# type: ignore
            Annuncio.objects.filter(inserzionista=user.id).delete() # type: ignore
            CommentoAnnuncio.objects.filter(utente=user.id).delete()# type: ignore
            Notification.objects.filter(recipient=user.id).delete()# type: ignore
        else:
            return HttpResponseForbidden()
        return redirect(f'{reverse("sylvelius:profile")}?evento=formatta_ut')
    else:
        return HttpResponseForbidden()
    
@require_POST
@login_required
def annulla_ordine(request, order_id):
    ordine = get_object_or_404(Ordine,id=order_id)
    if(request.user == ordine.utente and ordine.stato_consegna=='da spedire'):
        ordine.stato_consegna = 'annullato'
        ordine.save()
        return JsonResponse({"status": "success"})
    else: return JsonResponse({"status": "error", "message": "Ordine non trovato o già spedito"}, status=400)