from django.http import Http404, JsonResponse
from .models import ImmagineProdotto, Notification
from asgiref.sync import sync_to_async
from django.db.models import Q

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
    
    # Costruisci la lista degli URL
    immagini_urls = [img.immagine.url for img in immagini if img.immagine]
    if not immagini_urls:
        immagini_urls = ['/static/img/default_product.png']
        
    return JsonResponse({'urls': immagini_urls})

def notifications_api(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)
    
    notifications = Notification.objects.filter(
        Q(recipient=request.user) | 
        Q(is_global=True)
    ).order_by('created_at')[:20]
    
    data = [{
        'title': n.title,
        'message': n.message,
        'read': n.read,
        'date': n.created_at.isoformat()
    } for n in notifications]
    
    return JsonResponse(data, safe=False)
