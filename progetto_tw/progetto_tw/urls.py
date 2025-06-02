from django.contrib import admin
from django.urls import path, include
from .importa_dati import init_db, delete_db
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include("sylvelius.urls")),
    path('pagamento/', include("purchase.urls")),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # DA RIMUOVERE IN PRODUZIONE

delete_db()
init_db()