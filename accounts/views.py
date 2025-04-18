from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login
from django.core.mail import send_mail as send_mail_django
from django_ratelimit.decorators import ratelimit
import random, os

from .models import CustomUser, SelectedActivity

User = get_user_model()

def generate_otp():
    return str(random.randint(1000, 9999))

@ratelimit(key="user_or_ip", rate="5/m")
def send_mail(request, subject, message, recipient_list):
    print("[INFO] sending email", message)
    send_mail_django(
        subject,
        message,
        os.getenv("EMAIL_SENDER_FROM"),
        recipient_list,
        fail_silently=False,
    )

def signup_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        phonenumber = request.POST.get("phonenumber")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if not email or not phonenumber or not password or not password2:
            return render(request, "accounts/signup.html", {"error": "All fields are required."})

        if password != password2:
            return render(request, "accounts/signup.html", {"error": "Passwords do not match."})

        try:
            user = CustomUser.objects.create_user(
                email=email,
                phonenumber=phonenumber,
                password=password,
            )
            user.otp_email = "1234"  # For dev/testing
            user.save()
            request.session["email"] = user.email
            return redirect("accounts:otp")
        except IntegrityError as e:
            return render(request, "accounts/signup.html", {"error": str(e)})

    return render(request, "accounts/signup.html")

def otp_view(request):
    if request.method == "POST":
        otp_entered = str(request.POST.get("otp"))
        email = request.session.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return redirect("accounts:login")

        if otp_entered == user.otp_email:
            user.is_email_verified = True
            user.otp_email = ""
            user.save()
            login(request, user)
            return redirect("explore")

        return render(request, "accounts/otp.html", {"error": "Invalid OTP. Please try again."})

    return render(request, "accounts/otp.html")

def login_view(request):
    if request.method == "POST":
        identifier = request.POST.get("username").lower()
        password = request.POST.get("password")
        user = authenticate(username=identifier, password=password)

        if not user:
            return render(request, "accounts/login.html", {"error": "Incorrect Username or Password"})

        if not user.is_email_verified:
            otp = generate_otp()
            user.otp_email = otp
            user.save()
            send_mail(
                request,
                subject="Your OTP Code",
                message=f"Your OTP code is {otp}",
                recipient_list=[user.email],
            )
            request.session["email"] = user.email
            return redirect("accounts:otp")

        login(request, user)
        return redirect(request.GET.get("next", "index"))

    return render(request, "accounts/login.html")

def explore_view(request):
    if request.method == 'POST':
        selected = request.POST.getlist('activities')
        # Delete existing selections for this user
        SelectedActivity.objects.filter(user=request.user).delete()
        # Save new selections
        for activity in selected:
            SelectedActivity.objects.create(user=request.user, activity=activity)
        return redirect('index')
    else:
        # Fetch existing selections for GET request
        selected_activities = list(SelectedActivity.objects.filter(user=request.user).values_list('activity', flat=True))
        return render(request, 'explore.html', {'selected_activities': selected_activities})

    # For GET requests, retrieve selected activities
    if request.user.is_authenticated:
        selected_activities = list(SelectedActivity.objects.filter(user=request.user).values_list('activity', flat=True))
    else:
        selected_activities = request.session.get('selected_activities', [])

    return render(request, "accounts/explore.html", {"activities": activities, "selected_activities": selected_activities})

class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = "accounts/password_reset.html"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, please check your spam folder."
    )
    success_url = reverse_lazy("accounts:password_reset")

    def get_current_site(self):
        from django.contrib.sites.requests import RequestSite
        return RequestSite(self.request)

def index(request):
    return render(request, "Tamsha/index.html")

def cities_view(request):
    return render(request, 'accounts/cities.html', {})






# from django.urls import reverse_lazy
# from django.contrib.auth.views import PasswordResetView
# from django.contrib.messages.views import SuccessMessageMixin
# from django.db import IntegrityError
# from django.shortcuts import render, redirect
# from django.contrib.auth import get_user_model
# from django.contrib.auth import authenticate, login
# import random
# from django.core.mail import send_mail as send_mail_django
# from . import utils
# import os
# from django_ratelimit.decorators import ratelimit
# from django_ratelimit.exceptions import Ratelimited
#
# User = get_user_model()
#
#
# def generate_otp():
#     # Generate a random 4-digit OTP as a string
#     return str(random.randint(1000, 9999))
#
# def index(request):
#     return render(request, "Tamsha/index.html")
#
#
# def cities_view(request):  # not explore_view
#     return render(request, 'accounts/cities.html', {})
# @ratelimit(key="user_or_ip", rate="5/m")
# def send_mail(request, subject, message, recipient_list):
#     print("[INFO] sending email", message)
#
#     send_mail_django(
#         subject,
#         message,
#         os.getenv("EMAIL_SENDER_FROM"),
#         recipient_list,
#         fail_silently=False,
#     )
#
#
# def signup_view(request):
#     if request.method == "POST":
#         email = request.POST.get("email")
#         password = request.POST.get("password")
#         password2 = request.POST.get("password2")
#         phonenumber = request.POST.get("phonenumber")
#         firstName = request.POST.get("firstName")
#         lastName = request.POST.get("lastName")
#
#         if utils.is_empty(
#             [email, password, password2, phonenumber, firstName, lastName]
#         ):
#             return render(
#                 request, "accounts/signup.html", {"error": "All fields are required"}
#             )
#
#         if password != password2:
#             return render(
#                 request, "accounts/signup.html", {"error": "Passwords do not match"}
#             )
#
#         # Create a new user with unverified email status
#         try:
#             user = User.objects.create_user(
#                 email=email,
#                 password=password,
#                 phonenumber=phonenumber,
#                 first_name=firstName,
#                 last_name=lastName,
#             )
#         except IntegrityError:
#             return render(
#                 request,
#                 "accounts/signup.html",
#                 {"error": "Email or phone number already exists"},
#             )
#         user.is_email_verified = False
#         otp = generate_otp()
#         user.otp_email = otp
#         user.save()
#
#         # Send the OTP via email
#         send_mail(
#             request,
#             subject="Your OTP Code",
#             message=f"Your OTP code is {otp}",
#             recipient_list=[email],
#         )
#         # Store the email in session to identify the user in otp_view
#         request.session["email"] = email
#         return redirect("accounts:otp")
#
#     return render(request, "accounts/signup.html")
#
#
# def login_view(request):
#     if request.method == "POST":
#         identifier = request.POST.get(
#             "username"
#         ).lower()  # Could be email or phone number
#         password = request.POST.get("password")
#
#         user = authenticate(username=identifier, password=password)
#         if not user:
#             return render(
#                 request,
#                 "accounts/login.html",
#                 {"error": "Incorrect Username or Password"},
#             )
#
#         if not user.is_email_verified:
#             # Optionally, generate a new OTP on each login attempt
#             otp = generate_otp()
#             user.otp_email = otp
#             user.save()
#             send_mail(
#                 request,
#                 subject="Your OTP Code",
#                 message=f"Your OTP code is {otp}",
#                 recipient_list=[user.email],
#             )
#             # Save the email in session for use in otp_view
#             request.session["email"] = user.email
#             return redirect("accounts:otp")
#
#         login(request, user)
#
#         next_url = request.GET.get("next", "index")
#         print("next_url:", next_url)
#         return redirect(next_url)
#
#     return render(request, "accounts/login.html")
#
#
# def otp_view(request):
#     if request.method == "POST":
#         otp_entered = str(request.POST.get("otp"))
#         email = request.session.get("email")
#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return redirect("accounts:login")
#
#         print(
#             "user.otp_email:",
#             user.otp_email,
#             otp_entered,
#             otp_entered == user.otp_email,
#         )
#
#         if otp_entered == user.otp_email:
#             user.is_email_verified = True
#             user.otp_email = ""  # Clear OTP after successful verification
#             user.save()
#             login(request, user)
#             return redirect("index")
#         else:
#             return render(
#                 request,
#                 "accounts/otp.html",
#                 {"error": "Invalid OTP. Please try again."},
#             )
#
#     return render(request, "accounts/otp.html")
#
#
# class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
#     template_name = "accounts/password_reset.html"
#     # email_template_name = "accounts/password_reset_email.html"
#     # subject_template_name = "accounts/password_reset_subject"
#     success_message = (
#         "We've emailed you instructions for setting your password, "
#         "if an account exists with the email you entered. You should receive them shortly."
#         " If you don't receive an email, "
#         "please make sure you've entered the address you registered with, and check your spam folder."
#     )
#     success_url = reverse_lazy("accounts:password_reset")
#     # Removed static domain_override
#
#     def get_current_site(self):
#         # Dynamically retrieves the host (including port, if any) from the request.
#         from django.contrib.sites.requests import RequestSite
#
#         return RequestSite(self.request)
