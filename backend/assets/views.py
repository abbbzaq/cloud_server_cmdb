from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from auditlog.models import ChangeLog
from cmdb_backend.permissions import IsAdminOrOpsWriteElseRead
from .models import CloudAccount, CloudInstance
from .serializers import (
    CloudAccountSerializer,
    CloudInstanceRelationSerializer,
    CloudInstanceSerializer,
)


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


def get_operator(request):
    if request.user and request.user.is_authenticated:
        return request.user.username
    return "system"


def filter_instances(request, queryset):
    provider = request.query_params.get("provider")
    account_id = request.query_params.get("account_id")
    region = request.query_params.get("region")
    status_value = request.query_params.get("status")
    owner = request.query_params.get("owner")
    env = request.query_params.get("env")
    tag_key = request.query_params.get("tag_key")
    tag_value = request.query_params.get("tag_value")

    if provider:
        queryset = queryset.filter(account__provider=provider)
    if account_id:
        queryset = queryset.filter(account_id=account_id)
    if region:
        queryset = queryset.filter(region=region)
    if status_value:
        queryset = queryset.filter(status=status_value)
    if owner:
        queryset = queryset.filter(owner=owner)
    if env:
        queryset = queryset.filter(env=env)
    if tag_key:
        queryset = queryset.filter(tags__tag_key=tag_key)
    if tag_value:
        queryset = queryset.filter(tags__tag_value=tag_value)

    return queryset.distinct()


@api_view(["GET", "POST"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_account_list_create(request):
    if request.method == "GET":
        queryset = CloudAccount.objects.all().order_by("id")
        serializer = CloudAccountSerializer(queryset, many=True)
        return build_response("account_list", "获取成功", serializer.data)

    serializer = CloudAccountSerializer(data=request.data)
    if not serializer.is_valid():
        return build_response("account_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)

    obj = serializer.save()
    ChangeLog.objects.create(
        resource_type="cloud_account",
        resource_id=str(obj.id),
        field="create",
        old_value="",
        new_value=f"{obj.provider}:{obj.account_id}:{obj.project_name}",
        operator=get_operator(request),
        source="manual",
    )
    return build_response("account_create", "创建成功", CloudAccountSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_account_detail(request, pk):
    obj = get_object_or_404(CloudAccount, pk=pk)

    if request.method == "GET":
        return build_response("account_detail", "获取成功", CloudAccountSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        old_values = {
            "provider": obj.provider,
            "account_id": obj.account_id,
            "project_name": obj.project_name,
            "auth_ref": obj.auth_ref,
            "status": obj.status,
        }
        partial = request.method == "PATCH"
        serializer = CloudAccountSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response("account_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)

        updated_obj = serializer.save()
        change_logs = []
        for field_name, old_value in old_values.items():
            new_value = getattr(updated_obj, field_name)
            if old_value != new_value:
                change_logs.append(
                    ChangeLog(
                        resource_type="cloud_account",
                        resource_id=str(updated_obj.id),
                        field=field_name,
                        old_value=str(old_value),
                        new_value=str(new_value),
                        operator=get_operator(request),
                        source="manual",
                    )
                )
        if change_logs:
            ChangeLog.objects.bulk_create(change_logs)
        return build_response("account_update", "更新成功", CloudAccountSerializer(updated_obj).data)

    ChangeLog.objects.create(
        resource_type="cloud_account",
        resource_id=str(obj.id),
        field="delete",
        old_value=f"{obj.provider}:{obj.account_id}:{obj.project_name}",
        new_value="",
        operator=get_operator(request),
        source="manual",
    )
    obj.delete()
    return build_response("account_delete", "删除成功", [])


@api_view(["GET", "POST"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_list_create(request):
    if request.method == "GET":
        queryset = CloudInstance.objects.select_related("account").all().order_by("id")
        queryset = filter_instances(request, queryset)
        serializer = CloudInstanceSerializer(queryset, many=True)
        return build_response("instance_list", "获取成功", serializer.data)

    serializer = CloudInstanceSerializer(data=request.data)
    if not serializer.is_valid():
        return build_response("instance_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)

    obj = serializer.save()
    ChangeLog.objects.create(
        resource_type="cloud_instance",
        resource_id=obj.instance_id,
        field="create",
        old_value="",
        new_value=obj.name,
        operator=get_operator(request),
        source="manual",
    )
    return build_response("instance_create", "创建成功", CloudInstanceSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_detail(request, pk):
    queryset = CloudInstance.objects.select_related("account").prefetch_related("disks", "networks", "tags")
    obj = get_object_or_404(queryset, pk=pk)

    if request.method == "GET":
        return build_response("instance_detail", "获取成功", CloudInstanceSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        old_values = {
            "name": obj.name,
            "region": obj.region,
            "zone": obj.zone,
            "instance_type": obj.instance_type,
            "private_ip": obj.private_ip,
            "public_ip": obj.public_ip,
            "status": obj.status,
            "owner": obj.owner,
            "env": obj.env,
        }
        partial = request.method == "PATCH"
        serializer = CloudInstanceSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response("instance_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)

        updated_obj = serializer.save()
        change_logs = []
        for field_name, old_value in old_values.items():
            new_value = getattr(updated_obj, field_name)
            if old_value != new_value:
                change_logs.append(
                    ChangeLog(
                        resource_type="cloud_instance",
                        resource_id=updated_obj.instance_id,
                        field=field_name,
                        old_value=str(old_value),
                        new_value=str(new_value),
                        operator=get_operator(request),
                        source="manual",
                    )
                )
        if change_logs:
            ChangeLog.objects.bulk_create(change_logs)
        return build_response("instance_update", "更新成功", CloudInstanceSerializer(updated_obj).data)

    ChangeLog.objects.create(
        resource_type="cloud_instance",
        resource_id=obj.instance_id,
        field="delete",
        old_value=obj.name,
        new_value="",
        operator=get_operator(request),
        source="manual",
    )
    obj.delete()
    return build_response("instance_delete", "删除成功", [])


@api_view(["GET"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_relations(request, pk):
    queryset = CloudInstance.objects.select_related("account").prefetch_related("disks", "networks", "tags")
    obj = get_object_or_404(queryset, pk=pk)
    serializer = CloudInstanceRelationSerializer(obj)
    return build_response("instance_relations", "获取成功", serializer.data)


@api_view(["GET"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_alerts(request):
    required_tags = ["env", "business_unit", "owner", "cost_center", "service_name"]
    base_queryset = CloudInstance.objects.select_related("account").all().order_by("id")
    base_queryset = filter_instances(request, base_queryset)

    missing_owner = base_queryset.filter(Q(owner="") | Q(owner__isnull=True))
    missing_tags = base_queryset.annotate(
        required_tag_count=Count(
            "tags__tag_key",
            filter=Q(tags__tag_key__in=required_tags),
            distinct=True,
        )
    ).filter(required_tag_count__lt=len(required_tags))
    high_risk = base_queryset.filter(networks__inbound_rules__icontains="0.0.0.0/0").filter(
        Q(networks__inbound_rules__icontains="22") | Q(networks__inbound_rules__icontains="3389")
    )

    payload = {
        "required_tags": required_tags,
        "missing_owner_count": missing_owner.distinct().count(),
        "missing_tags_count": missing_tags.distinct().count(),
        "high_risk_port_count": high_risk.distinct().count(),
        "missing_owner_samples": list(missing_owner.values("id", "instance_id", "name")[:10]),
        "missing_tags_samples": list(missing_tags.values("id", "instance_id", "name")[:10]),
        "high_risk_port_samples": list(high_risk.values("id", "instance_id", "name")[:10]),
    }
    return build_response("instance_alerts", "获取成功", payload)
