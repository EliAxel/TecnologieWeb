from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView
from .models import Annuncio, Creazione, ImmagineProdotto, Ordine, Tag, Prodotto
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
import json
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

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
    success_url = reverse_lazy('sylvelius:home')

class LoginPageView(LoginView):
    template_name = "sylvelius/login.html"

class LogoutPageView(LogoutView):
    next_page = reverse_lazy('sylvelius:home')

class ProfiloPageView(LoginRequiredMixin, TemplateView):
    template_name = "sylvelius/profile.html"
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
            .filter(prodotto_id__in=prodotti_mie_creazioni, stato='in attesa')
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
        nome = request.POST.get('nome')
        descrizione = request.POST.get('descrizione')
        descrizione_breve = request.POST.get('descrizione_breve', '')  # opzionale
        prezzo = request.POST.get('prezzo')
        tag_string = request.POST.get('tags', '')  # è una stringa unica!
        immagini = request.FILES.getlist('immagini')
        qta_magazzino = request.POST.get('qta_magazzino', 0)

        # Validazione base
        if not nome or not descrizione or not prezzo:
            return render(request, self.template_name, {'tags': Tag.objects.all()})

        try:
            prezzo = float(prezzo)
        except ValueError:
            return render(request, self.template_name, {'tags': Tag.objects.all()})

        prodotto=Prodotto.objects.create(
                nome=nome,
                descrizione_breve=descrizione_breve,
                descrizione=descrizione,
                prezzo=prezzo
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

@require_POST
def check_username_exists(request):
    import json
    data = json.loads(request.body)
    username = data.get("username", "").strip()
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({"exists": exists})

@require_POST
def check_login_credentials(request):
    if request.method == "POST":
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
    return JsonResponse({"exists": False, "valid_password": False})