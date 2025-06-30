from django.contrib import admin
from .models import Invoice, Iban, Cart

# Register your models here.
admin.site.register(Invoice)
admin.site.register(Iban)
admin.site.register(Cart)