from django.contrib import admin
from django.urls import path, include
from .importa_dati import init_db, delete_db
from django.conf import settings
from django.conf.urls.static import static
from paypal.standard.ipn import urls as paypal_urls

urlpatterns = [
    path('', include("sylvelius.urls")),
    path('admin/', admin.site.urls),
    path('paypal/', include(paypal_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

#delete_db()
#init_db()