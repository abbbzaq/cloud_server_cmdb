from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cmdb_backend.permissions import IsCMDBMember
from .models import ChangeLog
from .serializers import ChangeLogSerializer


def build_response(action, msg, data, http_status=status.HTTP_200_OK, code=201):
    return Response(
        {
            "code": code,
            "module": "云服务器CMDB",
            "action": action,
            "msg": msg,
            "data": data,
        },
        status=http_status,
    )


@api_view(["GET"])
@permission_classes([IsCMDBMember])
def change_log_list(request):
    queryset = ChangeLog.objects.all().order_by("id")

    resource_type = request.query_params.get("resource_type")
    resource_id = request.query_params.get("resource_id")
    operator = request.query_params.get("operator")
    field = request.query_params.get("field")
    start_time = request.query_params.get("start_time")
    end_time = request.query_params.get("end_time")

    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)
    if resource_id:
        queryset = queryset.filter(resource_id=resource_id)
    if operator:
        queryset = queryset.filter(operator=operator)
    if field:
        queryset = queryset.filter(field=field)
    if start_time:
        queryset = queryset.filter(changed_at__gte=start_time)
    if end_time:
        queryset = queryset.filter(changed_at__lte=end_time)

    serializer = ChangeLogSerializer(queryset, many=True)
    return build_response("change_log_list", "获取成功", serializer.data)


@api_view(["GET"])
@permission_classes([IsCMDBMember])
def change_log_detail(request, pk):
    obj = get_object_or_404(ChangeLog, pk=pk)
    serializer = ChangeLogSerializer(obj)
    return build_response("change_log_detail", "获取成功", serializer.data)
