from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(response.data, dict) and (
        {"code", "message", "data"}.issubset(response.data.keys())
        or {"code", "msg", "data"}.issubset(response.data.keys())
    ):
        return response

    message = "error"
    if isinstance(response.data, dict) and isinstance(response.data.get("detail"), str):
        message = response.data["detail"]

    response.data = {
        "code": response.status_code,
        "msg": message,
        "data": response.data,
    }
    return response
