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
from .sync import (
    AliyunEcsInstanceProvider,
    CloudInstanceSyncService,
    MockTencentCloudInstanceProvider,
    MockUcloudInstanceProvider,
    ProviderConfigError,
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


@api_view(["GET"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_topology(request, pk):
    queryset = CloudInstance.objects.select_related("account").prefetch_related("disks", "networks", "tags")
    obj = get_object_or_404(queryset, pk=pk)

    nodes = [
        {
            "id": f"instance:{obj.instance_id}",
            "type": "instance",
            "label": obj.name,
            "meta": {
                "instance_id": obj.instance_id,
                "status": obj.status,
                "region": obj.region,
                "env": obj.env,
            },
        },
        {
            "id": f"account:{obj.account_id}",
            "type": "account",
            "label": obj.account.project_name,
            "meta": {
                "provider": obj.account.provider,
                "account_id": obj.account.account_id,
            },
        },
    ]
    edges = [
        {
            "from": f"instance:{obj.instance_id}",
            "to": f"account:{obj.account_id}",
            "relation": "belongs_to",
        }
    ]

    for disk in obj.disks.all():
        node_id = f"disk:{disk.disk_id}"
        nodes.append(
            {
                "id": node_id,
                "type": "disk",
                "label": disk.disk_id,
                "meta": {
                    "disk_type": disk.disk_type,
                    "size_gb": disk.size_gb,
                    "status": disk.status,
                },
            }
        )
        edges.append(
            {
                "from": f"instance:{obj.instance_id}",
                "to": node_id,
                "relation": "attached_to",
            }
        )

    for network in obj.networks.all():
        node_id = f"network:{network.id}"
        nodes.append(
            {
                "id": node_id,
                "type": "network",
                "label": network.subnet_id,
                "meta": {
                    "vpc_id": network.vpc_id,
                    "subnet_id": network.subnet_id,
                    "security_group_id": network.security_group_id,
                    "cidr": network.cidr,
                },
            }
        )
        edges.append(
            {
                "from": f"instance:{obj.instance_id}",
                "to": node_id,
                "relation": "connected_to",
            }
        )

    for tag in obj.tags.all():
        node_id = f"tag:{tag.id}"
        nodes.append(
            {
                "id": node_id,
                "type": "tag",
                "label": f"{tag.tag_key}={tag.tag_value}",
                "meta": {
                    "tag_key": tag.tag_key,
                    "tag_value": tag.tag_value,
                },
            }
        )
        edges.append(
            {
                "from": f"instance:{obj.instance_id}",
                "to": node_id,
                "relation": "has_tag",
            }
        )

    payload = {
        "center": {
            "id": obj.id,
            "instance_id": obj.instance_id,
            "name": obj.name,
        },
        "nodes": nodes,
        "edges": edges,
    }
    return build_response("instance_topology", "获取成功", payload)


@api_view(["POST"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_sync_aliyun(request):
    provider = "aliyun"
    account_id = request.data.get("account_id", "aliyun-account")
    project_name = request.data.get("project_name", "default-project")
    auth_ref = request.data.get("auth_ref", "kms://aliyun-ak")
    region = request.data.get("region", "cn-hangzhou")
    access_key_id = request.data.get("access_key_id", "")
    access_key_secret = request.data.get("access_key_secret", "")

    try:
        sync_provider = AliyunEcsInstanceProvider(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        )
        instances = sync_provider.list_instances(account_id=account_id, region=region)
    except ProviderConfigError as exc:
        return build_response("instance_sync_aliyun", str(exc), [], status.HTTP_400_BAD_REQUEST, 501)
    except Exception as exc:
        return build_response(
            "instance_sync_aliyun",
            f"阿里云同步失败: {exc}",
            [],
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            501,
        )

    result = CloudInstanceSyncService.sync_instances(
        provider=provider,
        account_id=account_id,
        project_name=project_name,
        auth_ref=auth_ref,
        instances=instances,
        operator=get_operator(request),
        source="cloud_sync",
    )
    return build_response("instance_sync_aliyun", "同步成功", result, status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_sync_tencent(request):
    provider = "tencent"
    account_id = request.data.get("account_id", "tencent-account")
    project_name = request.data.get("project_name", "default-project")
    auth_ref = request.data.get("auth_ref", "kms://tencent-secret")
    region = request.data.get("region", "ap-guangzhou")

    try:
        sync_provider = MockTencentCloudInstanceProvider()
        instances = sync_provider.list_instances(account_id=account_id, region=region)
    except ProviderConfigError as exc:
        return build_response("instance_sync_tencent", str(exc), [], status.HTTP_400_BAD_REQUEST, 501)
    except Exception as exc:
        return build_response(
            "instance_sync_tencent",
            f"腾讯云同步失败: {exc}",
            [],
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            501,
        )

    result = CloudInstanceSyncService.sync_instances(
        provider=provider,
        account_id=account_id,
        project_name=project_name,
        auth_ref=auth_ref,
        instances=instances,
        operator=get_operator(request),
        source="cloud_sync",
    )
    return build_response("instance_sync_tencent", "同步成功", result, status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_sync_ucloud(request):
    provider = "ucloud"
    account_id = request.data.get("account_id", "ucloud-account")
    project_name = request.data.get("project_name", "default-project")
    auth_ref = request.data.get("auth_ref", "kms://ucloud-secret")
    region = request.data.get("region", "cn-bj2")

    try:
        sync_provider = MockUcloudInstanceProvider()
        instances = sync_provider.list_instances(account_id=account_id, region=region)
    except ProviderConfigError as exc:
        return build_response("instance_sync_ucloud", str(exc), [], status.HTTP_400_BAD_REQUEST, 501)
    except Exception as exc:
        return build_response(
            "instance_sync_ucloud",
            f"UCloud 同步失败: {exc}",
            [],
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            501,
        )

    result = CloudInstanceSyncService.sync_instances(
        provider=provider,
        account_id=account_id,
        project_name=project_name,
        auth_ref=auth_ref,
        instances=instances,
        operator=get_operator(request),
        source="cloud_sync",
    )
    return build_response("instance_sync_ucloud", "同步成功", result, status.HTTP_201_CREATED)
