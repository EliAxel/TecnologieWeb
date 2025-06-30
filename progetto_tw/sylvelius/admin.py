from django.contrib import admin
from .models import (
    Tag,
    Prodotto,
    ImmagineProdotto,
    Annuncio,
    CommentoAnnuncio,
    Ordine,
    Notification
)
# Register your models here.
admin.site.register(Tag)
admin.site.register(Prodotto)
admin.site.register(ImmagineProdotto)
admin.site.register(Annuncio)
admin.site.register(CommentoAnnuncio)
admin.site.register(Ordine)
admin.site.register(Notification)