import json
import uuid

from PIL import Image

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.db.models.functions import Floor
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, TemplateView

from progetto_tw.constants import (
    ALIQUOTE_LIST_VALS,
    MAX_ANNUNCI_PER_DETTAGLI_VALUE,
    MAX_ANNU_QTA_MAGAZZINO_VALUE,
    MAX_COMMNT_RATING_VALUE,
    MAX_COMMNT_TESTO_CHARS,
    MAX_IMG_ASPECT_RATIO,
    MAX_IMG_SIZE,
    MAX_IMGS_PER_ANNU_VALUE,
    MAX_PAGINATOR_ANNUNCI_VALUE,
    MAX_PAGINATOR_BANNED_USERS_VALUE,
    MAX_PAGINATOR_COMMENTI_ANNUNCIO_VALUE,
    MAX_PAGINATOR_COMMENTI_DETTAGLI_VALUE,
    MAX_PAGINATOR_HOME_VALUE,
    MAX_PAGINATOR_ORDINI_VALUE,
    MAX_PAGINATOR_RICERCA_VALUE,
    MAX_PROD_DESC_BR_CHARS,
    MAX_PROD_DESC_CHARS,
    MAX_PROD_NOME_CHARS,
    MAX_PROD_PREZZO_VALUE,
    MAX_PWD_CHARS,
    MAX_TAGS_CHARS,
    MAX_TAGS_N_PER_PROD,
    MAX_UNAME_CHARS,
    MIN_CREA_ANNUNCIO_QTA_VALUE,
    MIN_COMMNT_RATING_VALUE,
    MIN_IMG_ASPECT_RATIO,
    MIN_PROD_PREZZO_VALUE,
    PROD_CONDIZIONE_CHOICES_ID,
    ADMIN_PROD_CONDIZIONE_CHOICES_ID,
    _MODS_GRP_NAME,
)
from progetto_tw.mixins import CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin

from purchase.models import Cart, Iban

from .forms import CustomUserCreationForm
from .models import (
    Annuncio,
    CommentoAnnuncio,
    ImmagineProdotto,
    Notification,
    Ordine,
    Prodotto,
    Tag,
)

@require_POST
@login_required
def mark_notifications_read(request):
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return JsonResponse({'status': 'ok'})
#non callable
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
#non callable
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
#non callable
def annulla_ordine_free(request, order_id):
    try:
        ordine = Ordine.objects.get(id=order_id)
    except Ordine.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Ordine non trovato o già spedito"
        }, status=400)
    if((request.user == ordine.utente or request.user == ordine.prodotto.annunci.inserzionista or request.user.groups.filter(name=_MODS_GRP_NAME).exists())): #type:ignore
        if request.user == ordine.utente and ordine.stato_consegna=='da spedire':
            ordine.stato_consegna = 'annullato'
            ordine.save()
            create_notification(recipient=ordine.prodotto.annunci.inserzionista,title="Ordine annullato", sender=request.user, #type:ignore
                                message=f"Il tuo ordine di {ordine.prodotto.nome} è stato annullato dal compratore")
        if ordine.stato_consegna=='da spedire' and request.user == ordine.prodotto.annunci.inserzionista:#type:ignore
            ordine.stato_consegna = 'annullato'
            ordine.save()
            create_notification(recipient=ordine.utente,title="Ordine rifiutato", sender=request.user, #type:ignore
                                message=f"Il tuo ordine di {ordine.prodotto.nome} è stato rifiutato dal venditore, riceverai un rimborso a breve")
        if request.user.groups.filter(name=_MODS_GRP_NAME).exists() and (ordine.stato_consegna=='da spedire' or ordine.stato_consegna=='spedito'):
            ordine.stato_consegna = 'annullato'
            ordine.save()
            create_notification(recipient=ordine.utente,title="Ordine cancellato", sender=request.user, #type:ignore
                                message=f"Il tuo ordine di {ordine.prodotto.nome} è stato cancellato da un moderatore, riceverai un rimborso a breve")
        return JsonResponse({"status": "success"})
    else: return JsonResponse({"status": "error", "message": "Ordine non trovato o già spedito"}, status=400)
#non callable
def check_if_annuncio_is_valid(request):
    nome = request.POST.get('nome').strip()
    descrizione = request.POST.get('descrizione', '')
    descrizione_breve = request.POST.get('descrizione_breve').strip()
    prezzo = request.POST.get('prezzo')
    iva = request.POST.get('iva')
    tag_string = request.POST.get('tags', '')
    immagini = request.FILES.getlist('immagini')
    qta_magazzino = request.POST.get('qta_magazzino', MIN_CREA_ANNUNCIO_QTA_VALUE)
    condizione = request.POST.get('condizione', 'nuovo')

    if condizione not in PROD_CONDIZIONE_CHOICES_ID:
        return {'evento': 'cond'}

    if not nome or not descrizione_breve or not prezzo:
        return {'evento': 'noval'}
    
    if (len(nome) > MAX_PROD_NOME_CHARS or
        len(descrizione_breve) > MAX_PROD_DESC_BR_CHARS or
        len(descrizione) > MAX_PROD_DESC_CHARS):
        return {'evento': 'lentxt'}
    
    try:
        prezzo = float(prezzo)
    except ValueError:
        return {'evento': 'prerr'}
    
    if prezzo < MIN_PROD_PREZZO_VALUE or prezzo > MAX_PROD_PREZZO_VALUE:
        return {'evento': 'price'}
    
    if iva not in ALIQUOTE_LIST_VALS:
        return {'evento': 'cond'}

    try:
        qta_magazzino = int(qta_magazzino)
    except ValueError:
        return {'evento': 'qtaerr'}
    if qta_magazzino < MIN_CREA_ANNUNCIO_QTA_VALUE or qta_magazzino > MAX_ANNU_QTA_MAGAZZINO_VALUE:
        return {'evento': 'qta'}
    
    tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
    if(len(tag_names)>MAX_TAGS_N_PER_PROD):
        return {'evento': 'tagn'}

    for nome in tag_names:
        if (len(nome) > MAX_TAGS_CHARS):
            return {'evento': 'tagchar'}
    
    if(len(immagini) > MAX_IMGS_PER_ANNU_VALUE):
        return {'evento': 'imgn'}
    
    for img in immagini:
        immagine = None
        try:
            immagine = Image.open(img)
            immagine.verify()
        except Exception:
            return {'evento': 'imgtype'}

        file_size = img.size
        if file_size > MAX_IMG_SIZE:
            return {'evento': 'imgsize'}
        
        width, height = immagine.size 
        aspect_ratio = width / height
        
        if aspect_ratio < MIN_IMG_ASPECT_RATIO or aspect_ratio > MAX_IMG_ASPECT_RATIO:
            return {'evento': 'imgproportion'}
    
    return None

class HomePageView(TemplateView):
    template_name = "sylvelius/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        annunci = Annuncio.objects.filter(is_published=True,qta_magazzino__gt=0,inserzionista__is_active=True).order_by('-data_pubblicazione')

        paginator = Paginator(annunci, MAX_PAGINATOR_HOME_VALUE)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context['annunci'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()

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

        if self.request.user.groups.filter(name=_MODS_GRP_NAME).exists():
            user_without_is_active_list = User.objects.filter(is_active=False).order_by('username')
            
            paginator = Paginator(user_without_is_active_list, MAX_PAGINATOR_BANNED_USERS_VALUE)
        
            page_number = self.request.GET.get('page',1)
            page_obj = paginator.get_page(page_number)
            
            context['user_without_is_active'] = page_obj.object_list
            context['page'] = page_obj.number
            context['has_next'] = page_obj.has_next()
            context['has_previous'] = page_obj.has_previous()
        else:
            utente = self.request.user
            context['user'] = utente
            context['annunci'] = Annuncio.objects.filter(inserzionista=utente).order_by('-data_pubblicazione')
            context['ordini'] = Ordine.objects.filter(utente=utente).order_by('-data_ordine')
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

            clienti = []
            for cliente, data in clienti_dict.items():
                cliente.ordini_da_rifornire = data['ordini_da_rifornire']
                clienti.append(cliente)

            context['clienti'] = clienti

        return context

class ProfiloDetailsPageView(View):
    template_name = 'sylvelius/profile/dettagli_profile.html'

    def get(self, request, user_profile):
        context = {}
        if request.user.groups.filter(name=_MODS_GRP_NAME).exists():
            user = get_object_or_404(User, username=user_profile)
            annunci = Annuncio.objects.filter(inserzionista=user).annotate(avg_rating=Avg('commenti__rating')).order_by('-avg_rating')
        else:
            user = get_object_or_404(User, username=user_profile, is_active=True)
            annunci = Annuncio.objects.filter(inserzionista=user,is_published=True).annotate(avg_rating=Avg('commenti__rating')).order_by('-avg_rating')
        if user.groups.filter(name=_MODS_GRP_NAME).exists():
            return HttpResponse(status=404)
        
        commenti = CommentoAnnuncio.objects.filter(utente=user,annuncio__inserzionista__is_active=True,annuncio__is_published=True).order_by('-data_pubblicazione')
        paginator = Paginator(commenti, MAX_PAGINATOR_COMMENTI_DETTAGLI_VALUE) 
        
        page_number = self.request.GET.get('page',1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            'user_profile': user,
            'annunci': annunci[:MAX_ANNUNCI_PER_DETTAGLI_VALUE],
            'annunci_count': annunci.count(),
            'commenti_count': commenti.count(),
        }
        context['commenti'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        return render(request, self.template_name, context)
    
class ProfiloEditPageView(CustomLoginRequiredMixin, View):
    template_name = "sylvelius/profile/profile_edit.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username').strip()
        old_password = request.POST.get('old_password')
        if not old_password:
            return render(request, self.template_name, {'evento': 'pwd'})
        else:
            old_password=old_password.strip()
            if not request.user.check_password(old_password):
                return render(request, self.template_name, {'evento': 'pwd'})
                
        new_password1 = request.POST.get('new_password1').strip()
        new_password2 = request.POST.get('new_password2').strip()

        if len(username) > MAX_UNAME_CHARS:
            return render(request, self.template_name, {'evento': 'usr'})
        if len(new_password1) > MAX_PWD_CHARS:
            return render(request, self.template_name, {'evento': 'pwd'})
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
            if User.objects.filter(username=username).exclude(pk=request.user.pk).exists():
                return render(request, self.template_name, {'evento': 'usr'})
            else:
                request.user.username = username
                request.user.save()

        if password_change_form_valid:
            update_session_auth_hash(request, request.user)
            return redirect(f'{reverse("sylvelius:profile")}?evento=profile_edit')
        else:
            return render(request, self.template_name, {'evento': 'pwd'})

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
            return render(request, self.template_name,{"evento":"ship"})
        if(Ordine.objects.filter(
            prodotto__annunci__inserzionista=user,
            stato_consegna='spedito'
            ).exists()):
            return render(request, self.template_name,{"evento":"shipd"})
        
        ordine_ex=Ordine.objects.filter(utente=user)
        ordine_in=Ordine.objects.filter(prodotto__annunci__inserzionista=user)
        
        for ordine in ordine_ex:
            annulla_ordine_free(request,ordine.id) #type:ignore
        
        for ordine in ordine_in:
            annulla_ordine_free(request,ordine.id) #type:ignore

        Annuncio.objects.filter(inserzionista=user).delete()
        Iban.objects.filter(utente=request.user).delete()
        Cart.objects.filter(utente=request.user).delete()
        CommentoAnnuncio.objects.filter(utente=request.user).delete()
        Notification.objects.filter(recipient=request.user).delete()
        logout(request)
        user.delete()
        return redirect('sylvelius:home')

class AnnuncioDetailView(TemplateView):
    template_name = "sylvelius/annuncio/dettagli_annuncio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        annuncio_uuid = self.kwargs['uuid']
        if self.request.user.groups.filter(name=_MODS_GRP_NAME).exists():
            annuncio = get_object_or_404(Annuncio, uuid=annuncio_uuid)
        else:
            annuncio = get_object_or_404(Annuncio, uuid=annuncio_uuid, is_published=True,inserzionista__is_active=True)

        context['get_commento'] = annUt = CommentoAnnuncio.objects.filter(
            annuncio=annuncio,
            utente=user
        ).first() if user.is_authenticated else None

        if self.request.user.groups.filter(name=_MODS_GRP_NAME).exists():
            if annUt:
                commenti = CommentoAnnuncio.objects.filter(
                    annuncio=annuncio
                ).exclude(id=annUt.id).select_related('utente').order_by('-data_pubblicazione') # type: ignore
            else:
                commenti = CommentoAnnuncio.objects.filter(
                    annuncio=annuncio
                ).select_related('utente').order_by('-data_pubblicazione')
        else:
            if annUt:
                commenti = CommentoAnnuncio.objects.filter(
                    annuncio=annuncio,
                    utente__is_active=True
                ).exclude(id=annUt.id).select_related('utente').order_by('-data_pubblicazione') # type: ignore
            else:
                commenti = CommentoAnnuncio.objects.filter(
                    annuncio=annuncio,
                    utente__is_active=True
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

        context['non_ha_commentato'] = non_ha_commentato
        context['ha_acquistato'] = ha_acquistato
        context['annuncio'] = annuncio

        paginator = Paginator(commenti, MAX_PAGINATOR_COMMENTI_ANNUNCIO_VALUE) 
        page_number = self.request.GET.get('page',1)
        page_obj = paginator.get_page(page_number)

        context['commenti'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        return context
    
class ProfiloOrdiniPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, TemplateView):
    template_name = "sylvelius/profile/profile_ordini.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        ordini_list = Ordine.objects.filter(utente=utente).order_by('-data_ordine')
        
        paginator = Paginator(ordini_list, MAX_PAGINATOR_ORDINI_VALUE)  
        page_number = self.request.GET.get('page',1)
        page_obj = paginator.get_page(page_number)
        
        context['ordini'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()

        return context
    
class ProfiloAnnunciPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, TemplateView):
    template_name = "sylvelius/profile/profile_annunci.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        annunci_list = Annuncio.objects.filter(inserzionista=utente).order_by('-data_pubblicazione')
        
        paginator = Paginator(annunci_list, MAX_PAGINATOR_ANNUNCI_VALUE)  
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['annunci'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()

        return context

class ProfiloCreaAnnuncioPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, View):
    template_name = "sylvelius/annuncio/crea_annuncio.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        err = check_if_annuncio_is_valid(request)
        if err:
            return render(request, self.template_name, err)
        
        nome = request.POST.get('nome').strip()
        descrizione = request.POST.get('descrizione', '')
        descrizione_breve = request.POST.get('descrizione_breve').strip()
        prezzo = request.POST.get('prezzo')
        iva = request.POST.get('iva')
        tag_string = request.POST.get('tags', '')
        immagini = request.FILES.getlist('immagini')
        qta_magazzino = request.POST.get('qta_magazzino', MIN_CREA_ANNUNCIO_QTA_VALUE)
        condizione = request.POST.get('condizione', 'nuovo')
        
        prodotto=Prodotto.objects.create(
            nome=nome,
            descrizione_breve=descrizione_breve,
            descrizione=descrizione,
            prezzo=prezzo,
            condizione=condizione,
            iva=int(iva)
        )
        annuncio = Annuncio.objects.create(
            uuid=uuid.uuid4(),
            inserzionista=request.user,
            prodotto=prodotto,
            data_pubblicazione=None,
            qta_magazzino=qta_magazzino,
            is_published=True
        )
            
        tag_instances = []
        tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
        for nome in tag_names:
            tag, _ = Tag.objects.get_or_create(nome=nome)
            tag_instances.append(tag)
            
        annuncio.prodotto.tags.set(tag_instances) 

        for img in immagini:
            ImmagineProdotto.objects.create(prodotto=prodotto, immagine=img)
        
        return redirect(f'{reverse("sylvelius:home")}?evento=crea_annuncio')

class ProfiloModificaAnnuncioPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, View):
    template_name = "sylvelius/annuncio/modifica_annuncio.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request, annuncio_id):
        ann_id = get_object_or_404(Annuncio,id=annuncio_id, inserzionista=request.user)
        context = {}
        context['titolo_mod'] = ann_id.prodotto.nome
        context['desc_br_mod'] = ann_id.prodotto.descrizione_breve
        context['desc_mod'] = ann_id.prodotto.descrizione
        context['prezzo_mod'] = ann_id.prodotto.prezzo
        context['iva_mod'] = ann_id.prodotto.iva
        context['qta_mod'] = ann_id.qta_magazzino
        context['cond_mod'] = ann_id.prodotto.condizione
        context['tags_mod'] = [tag.nome for tag in ann_id.prodotto.tags.all()]
        
        return render(request, self.template_name,context)
    
    def post(self,request,annuncio_id):
        err = check_if_annuncio_is_valid(request)
        if err:
            return render(request, self.template_name, err)

        nome = request.POST.get('nome').strip()
        descrizione = request.POST.get('descrizione', '')
        descrizione_breve = request.POST.get('descrizione_breve').strip()
        prezzo = request.POST.get('prezzo')
        iva = request.POST.get('iva')
        tag_string = request.POST.get('tags', '')
        immagini = request.FILES.getlist('immagini')
        qta_magazzino = request.POST.get('qta_magazzino', MIN_CREA_ANNUNCIO_QTA_VALUE)
        condizione = request.POST.get('condizione', 'nuovo')

        annuncio_mod=get_object_or_404(Annuncio,id=annuncio_id, inserzionista=request.user)

        prodotto = Prodotto.objects.get(id=annuncio_mod.prodotto.id)  # type:ignore
        prodotto.nome = nome
        prodotto.descrizione_breve = descrizione_breve
        prodotto.descrizione = descrizione
        prodotto.prezzo = prezzo #type:ignore
        prodotto.condizione = condizione
        prodotto.iva = int(iva)
        prodotto.save()

        annuncio = Annuncio.objects.get(id=annuncio_mod.id)  # type:ignore
        annuncio.uuid = annuncio_mod.uuid
        annuncio.inserzionista = request.user
        annuncio.prodotto = prodotto
        annuncio.data_pubblicazione = annuncio_mod.data_pubblicazione
        annuncio.qta_magazzino = qta_magazzino
        annuncio.is_published = annuncio_mod.is_published
        annuncio.save()

        tag_instances = []
        tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
        for nome in tag_names:
            tag, _ = Tag.objects.get_or_create(nome=nome)
            tag_instances.append(tag)
            
        annuncio.prodotto.tags.set(tag_instances)

        if len(immagini) > 0:
            ImmagineProdotto.objects.filter(prodotto=prodotto).delete()

        for img in immagini:
            ImmagineProdotto.objects.create(prodotto=prodotto, immagine=img)

        page = request.GET.get('page', 1)
        
        return redirect(f'{reverse("sylvelius:profile_annunci")}?page={page}&evento=mod_annuncio')
    
class ProfiloClientiPageView(CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin, TemplateView):
    template_name = "sylvelius/profile/profile_clienti.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        
        ordini_list = Ordine.objects.filter(prodotto__annunci__inserzionista=utente).select_related('prodotto', 'utente').order_by('-data_ordine')
        
        paginator = Paginator(ordini_list, MAX_PAGINATOR_ORDINI_VALUE)  
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['ordini'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()

        return context

class RicercaAnnunciView(TemplateView):
    template_name = "sylvelius/ricerca.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        categoria_str = self.request.GET.get('categoria', '').strip()
        inserzionista = self.request.GET.get('inserzionista', '').strip()
        prezzo_min = self.request.GET.get('prezzo_min')
        prezzo_max = self.request.GET.get('prezzo_max')
        sort_order = self.request.GET.get('sort', 'data-desc')
        condizione = self.request.GET.get('condition')
        rating = self.request.GET.get('search_by_rating')
        qta_mag = self.request.GET.get('qta_mag')

        annunci = Annuncio.objects.all()

        if query:
            annunci = annunci.filter(
                Q(prodotto__nome__icontains=query) |
                Q(prodotto__descrizione_breve__icontains=query) |
                Q(prodotto__tags__nome__icontains=query)
            )

        if categoria_str:
            tag_list = [tag.strip() for tag in categoria_str.split(',') if tag.strip()]
            for tag in tag_list:
                annunci = annunci.filter(prodotto__tags__nome=tag)
        
        if inserzionista != '':
            if self.request.user.groups.filter(name=_MODS_GRP_NAME).exists():
                annunci = annunci.filter(inserzionista__username=inserzionista)
            else:
                annunci = annunci.filter(inserzionista__username=inserzionista,inserzionista__is_active=True,is_published=True)
        elif not self.request.user.groups.filter(name=_MODS_GRP_NAME).exists():
            annunci = annunci.filter(inserzionista__is_active=True,is_published=True)
        
        if condizione in PROD_CONDIZIONE_CHOICES_ID:
            annunci = annunci.filter(prodotto__condizione=condizione)
        elif condizione in ADMIN_PROD_CONDIZIONE_CHOICES_ID:
            if condizione == 'nascosto':
                annunci = annunci.filter(is_published=False)
            else:
                annunci = annunci.filter(inserzionista__is_active=False)
        
        if qta_mag == 'qta-pres':
            annunci = annunci.filter(qta_magazzino__gt=0)
        elif qta_mag == 'qta-manc':
            annunci = annunci.filter(qta_magazzino=0)
        
        if rating:
            try:
                rating_value = int(rating)
                if MIN_COMMNT_RATING_VALUE <= rating_value <= MAX_COMMNT_RATING_VALUE:
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
                if rating == 'none':
                    annunci = annunci.exclude(commenti__isnull=False)
                elif rating == 'starred':
                    annunci = annunci.exclude(commenti__isnull=True)
                else:
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
        elif sort_order == "best-star":
            annunci = annunci.annotate(avg_rating=Avg('commenti__rating')).order_by('-avg_rating')
        elif sort_order == "worst-star":
            annunci = annunci.annotate(avg_rating=Avg('commenti__rating')).order_by('avg_rating')

        annunci = annunci.distinct()

        context['n_ris'] = annunci.count()
        paginator = Paginator(annunci, MAX_PAGINATOR_RICERCA_VALUE)
        page_number = self.request.GET.get('page', 1)

        page_obj = paginator.get_page(page_number)

        context['annunci'] = page_obj.object_list
        context['page'] = page_obj.number
        context['has_next'] = page_obj.has_next()
        context['has_previous'] = page_obj.has_previous()
        
        return context

@require_POST
@login_required
def toggle_pubblicazione(request, id):
    annuncio = get_object_or_404(Annuncio, id=id, inserzionista=request.user)
    annuncio.is_published = not annuncio.is_published
    annuncio.save()
    page = request.GET.get('page', 1)

    return redirect(f'{reverse("sylvelius:profile_annunci")}?page={page}&evento=nascondi')

@require_POST
@login_required
def delete_pubblicazione(request, id):
    if request.user.groups.filter(name=_MODS_GRP_NAME).exists():
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

    if (not testo or
        not rating.isdigit() or
        int(rating) < MIN_COMMNT_RATING_VALUE or
        int(rating) > MAX_COMMNT_RATING_VALUE or
        len(testo) > MAX_COMMNT_TESTO_CHARS):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "error", "message": "Dati non validi"}, status=400)
        return redirect(reverse('sylvelius:dettagli_annuncio', args=[annuncio.uuid]) + '?evento=commento_bad')

    commento = CommentoAnnuncio.objects.create(
        annuncio=annuncio,
        utente=utente,
        testo=testo,
        rating=int(rating)
    )
    commento.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "success"})

    return redirect(reverse('sylvelius:dettagli_annuncio', args=[annuncio.uuid]) + '?evento=commento_bad')

@require_POST
@login_required
def modifica_commento(request, commento_id):
    commento = get_object_or_404(CommentoAnnuncio, id=commento_id, utente=request.user)

    testo = request.POST.get('testo', '').strip()
    rating = request.POST.get('rating')

    if (not testo or
        not rating.isdigit() or
        int(rating) < MIN_COMMNT_RATING_VALUE or
        int(rating) > MAX_COMMNT_RATING_VALUE or
        len(testo) > MAX_COMMNT_TESTO_CHARS):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "error", "message": "Dati non validi"}, status=400)
        return redirect(reverse('sylvelius:dettagli_annuncio', args=[commento.annuncio.uuid]) + '?evento=commento_bad')

    commento.testo = testo
    commento.rating = int(rating)
    commento.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "success"})

    return redirect(reverse('sylvelius:dettagli_annuncio', args=[commento.annuncio.uuid]) + '?evento=commento_bad')

@require_POST
@login_required
def elimina_commento(request, commento_id):
    if request.user.groups.filter(name=_MODS_GRP_NAME).exists():
        commento = get_object_or_404(CommentoAnnuncio, id=commento_id)
        commento.delete()
    else:
        commento = get_object_or_404(CommentoAnnuncio, id=commento_id, utente=request.user)
        commento.delete()
    return JsonResponse({"status": "success"})

@require_POST
@login_required
def espelli_utente(request, is_active, user_id):
    if request.user.groups.filter(name=_MODS_GRP_NAME).exists():
        user = get_object_or_404(User, id=user_id)
        user.is_active = False if is_active=='ban' else True
        user.save()
        return redirect(f'{reverse("sylvelius:profile")}?evento=elimina_ut')
    else:
        return HttpResponseForbidden()

@require_POST
@login_required
def formatta_utente(request, user_id):
    if request.user.groups.filter(name=_MODS_GRP_NAME).exists():
        user = get_object_or_404(User, id=user_id)
        if(not user.is_active):
            ordini_ex = Ordine.objects.filter(prodotto__annunci__inserzionista=user)
            for ordine in ordini_ex:
                annulla_ordine_free(request,ordine.id)# type: ignore
            ordine_in = Ordine.objects.filter(utente=user)
            for ordine in ordine_in:
                annulla_ordine_free(request,ordine.id)# type: ignore
            ordine_in.delete()
            Annuncio.objects.filter(inserzionista=user.id).delete() # type: ignore
            CommentoAnnuncio.objects.filter(utente=user.id).delete()# type: ignore
            Cart.objects.filter(utente=user.id).delete()# type: ignore
            Iban.objects.filter(utente=user.id).delete()# type: ignore
            Notification.objects.filter(recipient=user.id).delete()# type: ignore
        else:
            return HttpResponseForbidden()
        return redirect(f'{reverse("sylvelius:profile")}?evento=formatta_ut')
    else:
        return HttpResponseForbidden()

@require_POST
@login_required
def annulla_ordine(request, order_id):
    return annulla_ordine_free(request, order_id)
