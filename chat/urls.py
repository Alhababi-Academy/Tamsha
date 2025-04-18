from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    path("", login_required(views.chat), name="index"),
    path("clear/", login_required(views.chat_clear), name="chat_clear"),
]

app_name = "chat"
