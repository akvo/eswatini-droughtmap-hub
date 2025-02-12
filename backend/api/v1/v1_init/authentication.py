from rest_framework import authentication, exceptions
from api.v1.v1_init.models import Settings


class SecretKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        secret_key = request.META.get('HTTP_X_SECRET_KEY')

        if not secret_key:
            return None  # No credentials provided
        try:
            settings = Settings.objects.get(secret_key=secret_key)
        except Settings.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid secret key')

        return (settings, None)  # Authenticated without a specific settings
