from .models import Profile
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"})
    )

class RegisterForm(UserCreationForm):
    full_name = forms.CharField(
        required=True,
        label="ФИО",
        widget=forms.TextInput(attrs={"placeholder": "Иванов Иван Иванович"})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"})
    )
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "username (необязательно)"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("full_name", "email", "username", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Этот email уже используется.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()

        if not user.username:
            user.username = user.email.split("@")[0][:150]

        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.full_name = self.cleaned_data["full_name"].strip()
            profile.save()

        return user
