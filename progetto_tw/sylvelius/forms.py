from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from progetto_tw.constants import MAX_UNAME_CHARS, MAX_PWD_CHARS

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=MAX_UNAME_CHARS,
        widget=forms.TextInput(attrs={'maxlength': f'{MAX_UNAME_CHARS}'}),
        help_text=f"Massimo {MAX_UNAME_CHARS} caratteri."
    )
    password1 = forms.CharField(
        max_length=MAX_PWD_CHARS,
        widget=forms.PasswordInput(attrs={'maxlength': f'{MAX_PWD_CHARS}'}),
        help_text=f"Massimo {MAX_PWD_CHARS} caratteri."
    )
    password2 = forms.CharField(
        max_length=MAX_PWD_CHARS,
        widget=forms.PasswordInput(attrs={'maxlength': f'{MAX_PWD_CHARS}'}),
        help_text="Inserisci la stessa password di prima, per verifica."
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2")