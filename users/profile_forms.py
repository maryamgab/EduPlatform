from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm

from .models import Profile

User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("full_name", "birth_date")
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Иванов Иван Иванович"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }


class TelegramNotificationsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            "telegram_notifications_enabled",
            "telegram_notify_new_lessons",
            "telegram_notify_new_quizzes",
            "telegram_notify_deadlines",
        )
        labels = {
            "telegram_notifications_enabled": "Включить уведомления в Telegram",
            "telegram_notify_new_lessons": "Новые уроки",
            "telegram_notify_new_quizzes": "Новые тесты",
            "telegram_notify_deadlines": "Приближающиеся дедлайны",
        }


class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label="Новая почта",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"})
    )
    password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Эта почта уже занята.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Неверный текущий пароль.")
        return password