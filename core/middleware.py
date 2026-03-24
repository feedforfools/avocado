from django.conf import settings
from django.contrib.auth import login


class AutoLoginMiddleware:
    """
    In DEBUG mode only: automatically log in the first superuser so you
    never have to hit a login form during local development.

    This middleware is a no-op when DEBUG is False — it is never active in
    production.  Add it to MIDDLEWARE *after* AuthenticationMiddleware so
    that request.user is already populated before we inspect it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG and not request.user.is_authenticated:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            dev_user = User.objects.filter(is_superuser=True).first()
            if dev_user:
                # backend is required when calling login() outside of a form
                dev_user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, dev_user)

        return self.get_response(request)
