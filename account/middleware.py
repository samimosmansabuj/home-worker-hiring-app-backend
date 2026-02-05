from django.utils import translation
from find_worker_config.model_choice import UserLanguage
from django.utils.translation import gettext_lazy as _

from django.utils import translation
from account.models import UserLanguage

class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            language = request.user.language or UserLanguage.EN
        elif request.session.get("language"):
            language = request.session["language"]
        else:
            language = UserLanguage.EN

        translation.activate(language)
        request.LANGUAGE_CODE = language

        response = self.get_response(request)

        translation.deactivate()
        return response

