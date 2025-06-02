from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=32,
        widget=forms.TextInput(attrs={'maxlength': '32'}),
        help_text="Massimo 32 caratteri."
    )
    password1 = forms.CharField(
        max_length=32,
        widget=forms.PasswordInput(attrs={'maxlength': '32'}),
        help_text="Massimo 32 caratteri."
    )
    password2 = forms.CharField(
        max_length=32,
        widget=forms.PasswordInput(attrs={'maxlength': '32'}),
        help_text="Inserisci la stessa password di prima, per verifica."
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username is None:
            raise forms.ValidationError("L'username è obbligatorio.")
        if len(username) > 32:
            raise forms.ValidationError("L'username non può superare i 32 caratteri.")
        return username

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1 is None:
            raise forms.ValidationError("La password è obbligatoria.")
        if len(password1) > 32:
            raise forms.ValidationError("La password non può superare i 32 caratteri.")
        return password1