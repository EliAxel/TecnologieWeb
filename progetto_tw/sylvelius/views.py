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

# Create your views here.
class HomePageView(TemplateView):
    template_name = "sylvelius/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['annunci'] = Annuncio.objects.all()
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
        context['creazioni'] = Creazione.objects.filter(utente=utente)
        context['ordini'] = Ordine.objects.filter(utente=utente) 
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