from rest_framework.renderers import JSONRenderer


class UnifiedJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        status_code = response.status_code if response else 200

        if status_code == 204:
            return super().render(data, accepted_media_type, renderer_context)

        if isinstance(data, dict) and (
            {"code", "message", "data"}.issubset(data.keys())
            or {"code", "msg", "data"}.issubset(data.keys())
        ):
            payload = data
        elif status_code >= 400:
            message = "error"
            if isinstance(data, dict) and isinstance(data.get("detail"), str):
                message = data["detail"]
            payload = {
                "code": status_code,
                "msg": message,
                "data": data,
            }
        else:
            payload = {
                "code": 0,
                "msg": "success",
                "data": data,
            }

        return super().render(payload, accepted_media_type, renderer_context)
