from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import RegisterForm, EmailAuthenticationForm

class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "registration/login.html"

def register(request):
    if request.user.is_authenticated:
        return redirect("course_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("course_list")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})
