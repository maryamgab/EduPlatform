from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Позволяет логиниться по email + пароль.
    При этом username остаётся в модели, но пользователю он не нужен.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Django передаёт поле логина как "username" (даже если это email)
        login = (username or kwargs.get("email") or "").strip().lower()
        if not login or not password:
            return None

        try:
            user = User.objects.get(email__iexact=login)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
