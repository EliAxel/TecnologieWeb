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

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username is None:
            raise forms.ValidationError("L'username è obbligatorio.")
        if len(username) > MAX_UNAME_CHARS:
            raise forms.ValidationError(f"L'username non può superare i {MAX_PWD_CHARS} caratteri.")
        return username

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1 is None:
            raise forms.ValidationError("La password è obbligatoria.")
        if len(password1) > MAX_PWD_CHARS:
            raise forms.ValidationError(f"La password non può superare i {MAX_PWD_CHARS} caratteri.")
        return password1