from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cmdb_backend.permissions import IsAdminOnly
from .models import SysGroup, SysGroupMenu, SysMenu, SysUser, SysUserGroup
from .serializers import (
    SysGroupMenuSerializer,
    SysGroupSerializer,
    SysMenuSerializer,
    SysUserGroupSerializer,
    SysUserSerializer,
)

User = get_user_model()

ROLE_GROUP_NAMES = {
    "admin": "管理员",
    "ops": "运维",
    "readonly": "只读",
}

ROLE_ALIASES = {
    "admin": {"admin", "administrator", "管理员"},
    "ops": {"ops", "operation", "运维"},
    "readonly": {"readonly", "read_only", "viewer", "只读"},
}


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


def normalize_role(value: str) -> str:
    text = (value or "").strip().lower()
    for role, aliases in ROLE_ALIASES.items():
        if text in aliases:
            return role
    return ""


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return build_response("login", "用户名和密码不能为空", [], status.HTTP_400_BAD_REQUEST, 501)

    user = authenticate(request=request, username=username, password=password)
    if not user:
        return build_response("login", "用户名或密码错误", [], status.HTTP_401_UNAUTHORIZED, 501)

    try:
        sys_user = SysUser.objects.select_related("user").get(user=user)
    except SysUser.DoesNotExist:
        sys_user = SysUser.objects.create(
            user=user,
            display_name=user.username,
            phone="",
            status="active",
        )
        readonly_group_name = ROLE_GROUP_NAMES["readonly"]
        readonly_group, _ = SysGroup.objects.get_or_create(
            group_name=readonly_group_name,
            defaults={"description": f"{readonly_group_name}角色", "status": "active"},
        )
        SysUserGroup.objects.get_or_create(user=user, group=readonly_group)

    if sys_user.status != "active":
        return build_response("login", "用户已禁用", [], status.HTTP_403_FORBIDDEN, 501)

    login(request, user)
    roles = list(SysUserGroup.objects.filter(user=user).values_list("group__group_name", flat=True))
    payload = {
        "user_id": user.id,
        "username": user.username,
        "display_name": sys_user.display_name,
        "roles": roles,
    }
    return build_response("login", "登录成功", payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return build_response("logout", "退出成功", [])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user
    try:
        sys_user = SysUser.objects.select_related("user").get(user=user)
    except SysUser.DoesNotExist:
        sys_user = SysUser.objects.create(
            user=user,
            display_name=user.username,
            phone="",
            status="active",
        )
        readonly_group_name = ROLE_GROUP_NAMES["readonly"]
        readonly_group, _ = SysGroup.objects.get_or_create(
            group_name=readonly_group_name,
            defaults={"description": f"{readonly_group_name}角色", "status": "active"},
        )
        SysUserGroup.objects.get_or_create(user=user, group=readonly_group)

    roles = list(SysUserGroup.objects.filter(user=user).values_list("group__group_name", flat=True))
    payload = {
        "user_id": user.id,
        "username": user.username,
        "display_name": sys_user.display_name,
        "status": sys_user.status,
        "roles": roles,
    }
    return build_response("current_user", "获取成功", payload)


@api_view(["GET", "POST"])
@permission_classes([IsAdminOnly])
def sys_user_list_create(request):
    if request.method == "GET":
        queryset = SysUser.objects.select_related("user").all().order_by("id")
        serializer = SysUserSerializer(queryset, many=True)
        return build_response("sys_user_list", "获取成功", serializer.data)

    payload = request.data.copy()
    username = payload.get("username")
    password = payload.get("password")
    created_user = None

    try:
        with transaction.atomic():
            if payload.get("user_id") is None and username and password:
                if User.objects.filter(username=username).exists():
                    return build_response(
                        "sys_user_create",
                        "用户名已存在",
                        {"username": ["该用户名已被使用。"]},
                        status.HTTP_400_BAD_REQUEST,
                        501,
                    )
                created_user = User.objects.create_user(username=username, password=password)
                created_user.is_staff = True
                created_user.save(update_fields=["is_staff"])
                payload["user_id"] = created_user.id

            serializer = SysUserSerializer(data=payload)
            if not serializer.is_valid():
                return build_response("sys_user_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)

            obj = serializer.save()

            readonly_group_name = ROLE_GROUP_NAMES["readonly"]
            readonly_group, _ = SysGroup.objects.get_or_create(
                group_name=readonly_group_name,
                defaults={"description": f"{readonly_group_name}角色", "status": "active"},
            )
            SysUserGroup.objects.get_or_create(user=obj.user, group=readonly_group)

    except Exception as exc:
        return build_response("sys_user_create", f"创建失败: {exc}", [], status.HTTP_500_INTERNAL_SERVER_ERROR, 501)

    return build_response("sys_user_create", "创建成功", SysUserSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOnly])
def sys_user_detail(request, pk):
    obj = get_object_or_404(SysUser.objects.select_related("user"), pk=pk)

    if request.method == "GET":
        return build_response("sys_user_detail", "获取成功", SysUserSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = SysUserSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response("sys_user_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
        updated_obj = serializer.save()
        return build_response("sys_user_update", "更新成功", SysUserSerializer(updated_obj).data)

    obj.delete()
    return build_response("sys_user_delete", "删除成功", [])


@api_view(["POST"])
@permission_classes([IsAdminOnly])
def assign_role(request):
    username = request.data.get("username")
    role = normalize_role(request.data.get("role"))

    if not username or not role:
        return build_response(
            "assign_role",
            "参数错误：username 与 role 必填，role 仅支持 admin/ops/readonly。",
            [],
            status.HTTP_400_BAD_REQUEST,
            501,
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return build_response("assign_role", "用户不存在。", [], status.HTTP_404_NOT_FOUND, 501)

    with transaction.atomic():
        target_group_name = ROLE_GROUP_NAMES[role]
        target_group, _ = SysGroup.objects.get_or_create(
            group_name=target_group_name,
            defaults={"description": f"{target_group_name}角色", "status": "active"},
        )

        role_group_names = list(ROLE_GROUP_NAMES.values())
        old_role_group_ids = SysGroup.objects.filter(group_name__in=role_group_names).values_list("id", flat=True)
        SysUserGroup.objects.filter(user=user, group_id__in=old_role_group_ids).delete()
        SysUserGroup.objects.get_or_create(user=user, group=target_group)

        user.is_staff = True
        user.is_superuser = role == "admin"
        user.save(update_fields=["is_staff", "is_superuser"])

    payload = {
        "username": user.username,
        "role": role,
        "group_name": target_group_name,
    }
    return build_response("assign_role", "分配成功", payload)


@api_view(["GET", "POST"])
@permission_classes([IsAdminOnly])
def sys_group_list_create(request):
    if request.method == "GET":
        queryset = SysGroup.objects.all().order_by("id")
        serializer = SysGroupSerializer(queryset, many=True)
        return build_response("sys_group_list", "获取成功", serializer.data)

    serializer = SysGroupSerializer(data=request.data)
    if not serializer.is_valid():
        return build_response("sys_group_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
    obj = serializer.save()
    return build_response("sys_group_create", "创建成功", SysGroupSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOnly])
def sys_group_detail(request, pk):
    obj = get_object_or_404(SysGroup, pk=pk)

    if request.method == "GET":
        return build_response("sys_group_detail", "获取成功", SysGroupSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = SysGroupSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response("sys_group_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
        updated_obj = serializer.save()
        return build_response("sys_group_update", "更新成功", SysGroupSerializer(updated_obj).data)

    obj.delete()
    return build_response("sys_group_delete", "删除成功", [])


@api_view(["GET", "POST"])
@permission_classes([IsAdminOnly])
def sys_menu_list_create(request):
    if request.method == "GET":
        queryset = SysMenu.objects.select_related("parent").all().order_by("id")
        serializer = SysMenuSerializer(queryset, many=True)
        return build_response("sys_menu_list", "获取成功", serializer.data)

    serializer = SysMenuSerializer(data=request.data)
    if not serializer.is_valid():
        return build_response("sys_menu_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
    obj = serializer.save()
    return build_response("sys_menu_create", "创建成功", SysMenuSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOnly])
def sys_menu_detail(request, pk):
    obj = get_object_or_404(SysMenu.objects.select_related("parent"), pk=pk)

    if request.method == "GET":
        return build_response("sys_menu_detail", "获取成功", SysMenuSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = SysMenuSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response("sys_menu_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
        updated_obj = serializer.save()
        return build_response("sys_menu_update", "更新成功", SysMenuSerializer(updated_obj).data)

    obj.delete()
    return build_response("sys_menu_delete", "删除成功", [])


@api_view(["GET", "POST"])
@permission_classes([IsAdminOnly])
def sys_user_group_list_create(request):
    if request.method == "GET":
        queryset = SysUserGroup.objects.select_related("user", "group").all().order_by("id")
        serializer = SysUserGroupSerializer(queryset, many=True)
        return build_response("sys_user_group_list", "获取成功", serializer.data)

    serializer = SysUserGroupSerializer(data=request.data)
    if not serializer.is_valid():
        return build_response("sys_user_group_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
    obj = serializer.save()
    return build_response("sys_user_group_create", "创建成功", SysUserGroupSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOnly])
def sys_user_group_detail(request, pk):
    obj = get_object_or_404(SysUserGroup.objects.select_related("user", "group"), pk=pk)

    if request.method == "GET":
        return build_response("sys_user_group_detail", "获取成功", SysUserGroupSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = SysUserGroupSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response(
                "sys_user_group_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501
            )
        updated_obj = serializer.save()
        return build_response("sys_user_group_update", "更新成功", SysUserGroupSerializer(updated_obj).data)

    obj.delete()
    return build_response("sys_user_group_delete", "删除成功", [])


@api_view(["GET", "POST"])
@permission_classes([IsAdminOnly])
def sys_group_menu_list_create(request):
    if request.method == "GET":
        queryset = SysGroupMenu.objects.select_related("group", "menu").all().order_by("id")
        serializer = SysGroupMenuSerializer(queryset, many=True)
        return build_response("sys_group_menu_list", "获取成功", serializer.data)

    serializer = SysGroupMenuSerializer(data=request.data)
    if not serializer.is_valid():
        return build_response("sys_group_menu_create", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501)
    obj = serializer.save()
    return build_response("sys_group_menu_create", "创建成功", SysGroupMenuSerializer(obj).data, status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAdminOnly])
def sys_group_menu_detail(request, pk):
    obj = get_object_or_404(SysGroupMenu.objects.select_related("group", "menu"), pk=pk)

    if request.method == "GET":
        return build_response("sys_group_menu_detail", "获取成功", SysGroupMenuSerializer(obj).data)

    if request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = SysGroupMenuSerializer(instance=obj, data=request.data, partial=partial)
        if not serializer.is_valid():
            return build_response(
                "sys_group_menu_update", "参数校验失败", serializer.errors, status.HTTP_400_BAD_REQUEST, 501
            )
        updated_obj = serializer.save()
        return build_response("sys_group_menu_update", "更新成功", SysGroupMenuSerializer(updated_obj).data)

    obj.delete()
    return build_response("sys_group_menu_delete", "删除成功", [])
