from django.urls import path
from django.shortcuts import redirect
from . import views
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views



def require_not_loggedin(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("index")
        return view_func(request, *args, **kwargs)

    return wrapper


urlpatterns = [
    path("signup/", require_not_loggedin(views.signup_view), name="signup"),
    path("signup/otp", require_not_loggedin(views.otp_view), name="otp"),
    path("login/", require_not_loggedin(views.login_view), name="login"),
    path("logout/", LogoutView.as_view(next_page="index"), name="logout"),
    path("password_reset/", views.ResetPasswordView.as_view(), name="password_reset"),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

app_name = "accounts"
