from django.urls import path

from .views import (
    assign_role,
    current_user,
    login_view,
    logout_view,
    refresh_token_view,
    sys_group_detail,
    sys_group_list_create,
    sys_group_menu_detail,
    sys_group_menu_list_create,
    sys_menu_detail,
    sys_menu_list_create,
    sys_user_detail,
    sys_user_group_detail,
    sys_user_group_list_create,
    sys_user_list_create,
)

urlpatterns = [
    path("login/", login_view, name="iam-login"),
    path("token/refresh/", refresh_token_view, name="iam-token-refresh"),
    path("logout/", logout_view, name="iam-logout"),
    path("me/", current_user, name="iam-current-user"),
    path("users/", sys_user_list_create, name="sysuser-list-create"),
    path("users/<int:pk>/", sys_user_detail, name="sysuser-detail"),
    path("users/assign-role/", assign_role, name="sysuser-assign-role"),
    path("groups/", sys_group_list_create, name="sysgroup-list-create"),
    path("groups/<int:pk>/", sys_group_detail, name="sysgroup-detail"),
    path("menus/", sys_menu_list_create, name="sysmenu-list-create"),
    path("menus/<int:pk>/", sys_menu_detail, name="sysmenu-detail"),
    path("user-groups/", sys_user_group_list_create, name="sysusergroup-list-create"),
    path("user-groups/<int:pk>/", sys_user_group_detail, name="sysusergroup-detail"),
    path("group-menus/", sys_group_menu_list_create, name="sysgroupmenu-list-create"),
    path("group-menus/<int:pk>/", sys_group_menu_detail, name="sysgroupmenu-detail"),
]
