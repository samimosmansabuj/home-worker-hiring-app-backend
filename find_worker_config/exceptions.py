from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status as drf_status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        message = ""
        if isinstance(response.data, dict):
            message = response.data.get("detail") or next(iter(response.data.values()), [""])[0]
        else:
            message = str(response.data)

        custom_response = {
            "status": False,
            "message": message
        }
        response.data = custom_response
    else:
        return Response(
            {"status": False, "message": str(exc)},
            status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return response

