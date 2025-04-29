from django.conf import settings
from django.shortcuts import redirect

class ConditionalSSLRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if already secure or not configured to redirect
        if request.is_secure() or not settings.SECURE_SSL_REDIRECT:
            return self.get_response(request)

        # Skip redirect if it's the /metrics path
        if request.path.startswith("/metrics"):
            return self.get_response(request)

        # Otherwise, enforce HTTPS redirect
        return redirect(f"https://{request.get_host()}{request.get_full_path()}")

