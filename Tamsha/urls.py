from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from Tamsha.views import index, explore as explore_view  # ✅ fixed here
from accounts.views import cities_view


def test_view(request):
    print(request.META)
    print("HOST IS:", request.get_host())
    return HttpResponse(request.get_host())

urlpatterns = [
    path("admin/", admin.site.urls),
    path("chat/", include("chat.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("explore/", explore_view, name="explore"),
    path('cities/', cities_view, name='city'),
    path("test/", test_view),
    path("", index, name="index"),
]
