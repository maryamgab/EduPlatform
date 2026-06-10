from django.conf import settings # импорт настроек проекта, почты
from django.contrib.auth import views as auth_views # импорт встроенных функции Django для авторизации и тд 

class PrettyPasswordResetView(auth_views.PasswordResetView):
    def get_email_options(self):
        opts = super().get_email_options() or {}
        opts.setdefault("subject_template_name", "registration/password_reset_subject.txt") # шаблон для темы письма
        opts.setdefault("email_template_name", "registration/password_reset_email.txt") # шаблон для письма
        return opts # возвращение готовых настроек письма

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs) # берется стандартные контексты страницы
        ctx["domain"] = getattr(settings, "DEFAULT_DOMAIN", "127.0.0.1:8000") # добавление запасного домена
        ctx["site_name"] = "Edu Platform" # добавление названия сайта
        return ctx # возаращение обновленного контекста

