from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class AuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # If the input contains '@', assume it's an email; otherwise, assume it's a phone number.
            if "@" in username:
                user = UserModel.objects.get(email=username)
            else:
                user = UserModel.objects.get(phonenumber=username)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password):
            return user

        return None
