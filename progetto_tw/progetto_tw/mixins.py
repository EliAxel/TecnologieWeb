from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import resolve_url
from django.core.exceptions import PermissionDenied
from .constants import _MODS_GRP_NAME

class CustomLoginRequiredMixin(LoginRequiredMixin):
    def get_login_url(self):
        login_url = super().get_login_url()
        return f"{resolve_url(login_url)}?auth=error"

class ModeratoreAccessForbiddenMixin:
    def dispatch(self, request, *args, **kwargs):
        # Controlla se l'utente è autenticato prima di accedere ai gruppi
        if request.user.is_authenticated:
            # .exists() è più efficiente che caricare l'intero gruppo
            if request.user.groups.filter(name=_MODS_GRP_NAME).exists():
                raise PermissionDenied 
        # Se l'utente non è un moderatore, procedi normalmente
        return super().dispatch(request, *args, **kwargs) # type: ignore