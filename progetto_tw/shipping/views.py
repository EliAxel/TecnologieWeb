from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from progetto_tw.mixins import CustomLoginRequiredMixin, ModeratoreAccessForbiddenMixin
from sylvelius.views import create_notification
from sylvelius.models import Ordine
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
# Create your views here.
class SpedizionePageView(CustomLoginRequiredMixin,ModeratoreAccessForbiddenMixin,TemplateView):
    template_name = "shipping/spedizione.html"
    login_url = reverse_lazy('sylvelius:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ordine = get_object_or_404(Ordine,id=self.request.GET.get('ordine'),prodotto__annunci__inserzionista=self.request.user, stato_consegna='da spedire')
        context['page'] = self.request.GET.get('page')
        context['ordine'] = ordine
        return context
    
@login_required
@require_POST
def imposta_spedito(request, ordine_id):
    ordine = get_object_or_404(Ordine,id=ordine_id,prodotto__annunci__inserzionista=request.user, stato_consegna='da spedire')
    ordine.stato_consegna = 'spedito'
    ordine.save()
    page = request.GET.get('page')
    create_notification(recipient=ordine.utente,title="Ordine spedito!", sender=request.user,
                                    message=f"Il tuo ordine di {ordine.prodotto.nome} è stato spedito!")
    create_notification(recipient=ordine.prodotto.annunci.inserzionista,title="Ordine spedito!", sender=request.user,#type:ignore
                                    message=f"Il tuo ordine di {ordine.prodotto.nome} per {ordine.utente} è stato spedito!")

    return redirect(f'{reverse("sylvelius:profile_clienti")}?page={page}&evento=spedito_ordine')

@login_required
@require_POST
def imposta_completato(request, ordine_id):
    ordine = get_object_or_404(Ordine,id=ordine_id,prodotto__annunci__inserzionista=request.user, stato_consegna='da spedire')
    ordine.stato_consegna = 'consegnato'
    ordine.save()
    create_notification(recipient=ordine.utente,title="Ordine consegnato!", sender=request.user,
                                    message=f"Il tuo ordine di {ordine.prodotto.nome} è stato consegnato!")
    create_notification(recipient=ordine.prodotto.annunci.inserzionista,title="Ordine consegnato!", sender=request.user, #type:ignore
                                    message=f"Il tuo ordine di {ordine.prodotto.nome} per {ordine.utente} è stato consegnato!")
    page = request.GET.get('page')
    return redirect(f'{reverse("sylvelius:profile_clienti")}?page={page}&evento=completato_ordine')