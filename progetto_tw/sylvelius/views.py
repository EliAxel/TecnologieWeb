from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView
from .models import Annuncio, Creazione, Ordine
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator

# Create your views here.
class HomePageView(TemplateView):
    template_name = "sylvelius/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filtro = self.request.GET.get('filtro')
        annunci = Annuncio.objects.all()
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
        context = super().get_context_data(**kwargs)
        utente = self.request.user
        context['user'] = utente
        context['creazioni'] = Creazione.objects.filter(utente=utente).order_by('-data_creazione')
        context['ordini'] = Ordine.objects.filter(utente=utente).order_by('-data_ordine')
        return context

class ProfiloEditPageView(LoginRequiredMixin, View):
    template_name = "sylvelius/profile_edit.html"
    login_url = reverse_lazy('sylvelius:login')

    def get(self, request):
        return render(request, self.template_name, {'user': request.user})

    def post(self, request):
        user = request.user
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)

        password = request.POST.get('password')
        if password:
            user.set_password(password)
            update_session_auth_hash(request, user)

        user.save()
        messages.success(request, "Profilo aggiornato con successo.")
        return redirect('sylvelius:profile')  # o dove vuoi tu


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
        context['annuncio'] = Annuncio.objects.get(id=annuncio_id)
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