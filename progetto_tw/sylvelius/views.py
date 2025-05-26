from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView
from .models import Annuncio, Creazione, ImmagineAnnuncio, Ordine, Tag
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
import json
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from functools import reduce
import operator

# Create your views here.
class HomePageView(TemplateView):
    template_name = "sylvelius/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filtro = self.request.GET.get('filtro')
        annunci = Annuncio.objects.filter(is_published=True).order_by('-data_pubblicazione')
        if filtro:
            annunci = annunci.filter(categoria=filtro)

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
    success_url = reverse_lazy('sylvelius:home')

class LoginPageView(LoginView):
    template_name = "sylvelius/login.html"

class LogoutPageView(LogoutView):
    next_page = reverse_lazy('sylvelius:home')

class ProfiloPageView(LoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        User = get_user_model()
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        context['creazioni'] = Creazione.objects.filter(utente=utente).order_by('-data_creazione')
        context['ordini'] = Ordine.objects.filter(utente=utente).order_by('-data_ordine')

        # Trova tutti gli utenti che hanno fatto ordini su annunci creati dall'utente corrente
        # e per cui almeno un ordine è "in attesa"
        mie_creazioni = Creazione.objects.filter(utente=utente).values_list('annuncio_id', flat=True)
        ordini_clienti = (
            Ordine.objects
            .filter(annuncio_id__in=mie_creazioni, stato='in attesa')
            .select_related('utente', 'annuncio')
        )

        clienti_dict = {}
        for ordine in ordini_clienti:
            cliente = ordine.utente
            if cliente not in clienti_dict:
                clienti_dict[cliente] = {
                    'username': cliente.username,
                    'email': cliente.email,
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

class ProfiloEditPageView(LoginRequiredMixin, View):
    template_name = "sylvelius/profile_edit.html"
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
            messages.error(request, "La vecchia password non è corretta.")
            return render(request, self.template_name, {'user': user})

        # Aggiorna username se cambiato
        if username and username != user.username:
            user.username = username

        # Gestione cambio password
        if new_password1 or new_password2:
            if new_password1 != new_password2:
                messages.error(request, "Le nuove password non coincidono.")
                return render(request, self.template_name, {'user': user})
            if new_password1:
                user.set_password(new_password1)
                update_session_auth_hash(request, user)

        user.save()
        messages.success(request, "Profilo aggiornato con successo.")
        return redirect('sylvelius:profile')


class ProfiloDeletePageView(LoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile_delete.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

class AnnuncioDetailView(TemplateView):
    template_name = "sylvelius/dettagli_annuncio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        annuncio_id = self.kwargs['pk']
        annuncio = get_object_or_404(Annuncio, id=annuncio_id, is_published=True)
        context['annuncio'] = annuncio
        return context
    
class ProfiloOrdiniPageView(LoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile_ordini.html"
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
    
class ProfiloCreazioniPageView(LoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile_creazioni.html"
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

class ProfiloCreaCreazionePageView(LoginRequiredMixin, View):
    template_name = "sylvelius/crea_annuncio.html"
    login_url = "sylvelius:login"

    def get(self, request):
        tags = Tag.objects.all()
        return render(request, self.template_name, {'tags': tags})

    def post(self, request):
        titolo = request.POST.get('titolo')
        descrizione = request.POST.get('descrizione')
        prezzo = request.POST.get('prezzo')
        tag_string = request.POST.get('tags', '')  # è una stringa unica!
        immagini = request.FILES.getlist('immagini')

        # Validazione base
        if not titolo or not descrizione or not prezzo:
            messages.error(request, "Compila tutti i campi obbligatori.")
            return render(request, self.template_name, {'tags': Tag.objects.all()})

        try:
            prezzo = float(prezzo)
        except ValueError:
            messages.error(request, "Il prezzo non è valido.")
            return render(request, self.template_name, {'tags': Tag.objects.all()})

        # Creazione dell'annuncio
        annuncio = Annuncio.objects.create(
            titolo=titolo,
            descrizione=descrizione,
            prezzo=prezzo
        )

        # Gestione dei tag (split manuale)
        tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
        tag_instances = []
        for nome in tag_names:
            tag, _ = Tag.objects.get_or_create(nome=nome)
            tag_instances.append(tag)
        annuncio.tags.set(tag_instances)

        # Salva immagini
        for img in immagini:
            ImmagineAnnuncio.objects.create(annuncio=annuncio, immagine=img)

        # Crea la creazione associata all'utente
        Creazione.objects.create(
            utente=request.user,
            annuncio=annuncio
        )

        messages.success(request, "Annuncio creato con successo!")
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

        annunci = Annuncio.objects.filter(is_published=True)

        if query:
            annunci = annunci.filter(
                Q(titolo__icontains=query) |
                Q(descrizione__icontains=query) |
                Q(tags__nome__icontains=query)
            )

        if categoria_str:
            tag_list = [tag.strip() for tag in categoria_str.split(',') if tag.strip()]
            if tag_list:
                for tag in tag_list:
                    annunci = annunci.filter(tags__nome=tag)


        if prezzo_min:
            try:
                annunci = annunci.filter(prezzo__gte=float(prezzo_min))
            except ValueError:
                pass

        if prezzo_max:
            try:
                annunci = annunci.filter(prezzo__lte=float(prezzo_max))
            except ValueError:
                pass

        if sort_order == "data-desc":
            annunci = annunci.order_by('-data_pubblicazione')
        elif sort_order == "data-asc":
            annunci = annunci.order_by('data_pubblicazione')
        elif sort_order == "prezzo-asc":
            annunci = annunci.order_by('prezzo')
        elif sort_order == "prezzo-desc":
            annunci = annunci.order_by('-prezzo')

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

@login_required
def check_old_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        old_password = data.get('old_password', '')

        if request.user.check_password(old_password):
            return JsonResponse({'valid': True})
        else:
            return JsonResponse({'valid': False})
    return JsonResponse({'valid': False}, status=400)
