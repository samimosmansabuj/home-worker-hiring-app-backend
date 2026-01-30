from django.utils import translation
from find_worker_config.model_choice import UserLanguage

class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("request.user.is_authenticated: ", request.user.is_authenticated)
        if request.user.is_authenticated:
            language = request.user.language or UserLanguage.EN
            translation.activate(language)
            request.LANGUAGE_CODE = language
        else:
            translation.activate(UserLanguage.EN)
        response = self.get_response(request)

        print("request: ", request.GET)
        print("translation: ", translation.get_language())
        translation.deactivate()
        return response
