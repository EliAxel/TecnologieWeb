from django.http import Http404, JsonResponse
from .models import ImmagineProdotto
from asgiref.sync import sync_to_async

async def get_immagine_prodotto(request, prodotto_id):
    immagini = await sync_to_async(list)(ImmagineProdotto.objects.filter(prodotto_id=prodotto_id).order_by('id')[:1])
    if immagini and immagini[0].immagine:
        return JsonResponse({'url': immagini[0].immagine.url})
    else:
        return JsonResponse({'url': '/static/img/default_product.png'})

async def get_immagini_prodotto(request, prodotto_id):
    # Ottieni le immagini in modo asincrono
    immagini = await sync_to_async(list)(
        ImmagineProdotto.objects.filter(prodotto_id=prodotto_id).order_by('id')
    )

    # Verifica se ci sono immagini
    if not immagini:
        raise Http404("Nessuna immagine trovata")

    # Costruisci la lista degli URL
    immagini_urls = [img.immagine.url for img in immagini]

    return JsonResponse({'immagini': immagini_urls})
