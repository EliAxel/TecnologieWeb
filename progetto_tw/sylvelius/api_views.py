from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from .models import ImmagineProdotto, Notification
from progetto_tw.constants import MAX_MESSAGES_PER_PAGE
from purchase.models import Cart

async def get_immagine_prodotto(request, prodotto_id):
    immagini = await sync_to_async(list)(ImmagineProdotto.objects.filter(prodotto_id=prodotto_id).order_by('id')[:1])
    if immagini and immagini[0].immagine:
        return JsonResponse({'url': immagini[0].immagine.url})
    else:
        return JsonResponse({'url': '/static/img/default_product.png'})

async def get_immagini_prodotto(request, prodotto_id):
    immagini = await sync_to_async(list)(
        ImmagineProdotto.objects.filter(prodotto_id=prodotto_id).order_by('id')
    )
    
    immagini_urls = [img.immagine.url for img in immagini if img.immagine]
    if not immagini_urls:
        immagini_urls = ['/static/img/default_product.png']
        
    return JsonResponse({'urls': immagini_urls})

async def notifications_api(request):
    is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
    if not is_authenticated:
        return JsonResponse([], safe=False)
    
    notifications = await sync_to_async(list)(
        Notification.objects.filter(
            Q(recipient=request.user) | 
            Q(is_global=True)
        ).order_by('created_at')[:MAX_MESSAGES_PER_PAGE]
    )
    
    data = [{
        'title': n.title,
        'message': n.message,
        'read': n.read,
        'date': n.created_at.isoformat()
    } for n in notifications]
    
    return JsonResponse(data, safe=False)

@login_required
def cart_check(request):
    try:
        cart = request.user.cart
        count = cart.invoices.count()
        return JsonResponse({'count': count})
    except Cart.DoesNotExist:
        return JsonResponse({'count': 0})