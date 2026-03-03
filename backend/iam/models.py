from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class SysUser(models.Model):
	user = models.OneToOneField(
		User,
		verbose_name="系统用户",
		on_delete=models.CASCADE,
		related_name="sys_profile",
	)
	display_name = models.CharField("显示名称", max_length=64)
	phone = models.CharField("手机号", max_length=32, blank=True)
	status = models.CharField("状态", max_length=16, default="active")
	created_at = models.DateTimeField("创建时间", auto_now_add=True)
	updated_at = models.DateTimeField("更新时间", auto_now=True)

	class Meta:
		db_table = "sys_user"
		verbose_name = "用户资料"
		verbose_name_plural = "用户资料"


class SysGroup(models.Model):
    group_name = models.CharField("用户组名称", max_length=64, unique=True)
    description = models.CharField("描述", max_length=255, blank=True)
    status = models.CharField("状态", max_length=16, default="active")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "sys_group"
        verbose_name = "用户组"
        verbose_name_plural = "用户组"

    def __str__(self):
        return self.group_name


class SysUserGroup(models.Model):
    user = models.ForeignKey(User, verbose_name="系统用户", on_delete=models.CASCADE)
    group = models.ForeignKey(SysGroup, verbose_name="用户组", on_delete=models.CASCADE)

    class Meta:
        db_table = "sys_user_group"
        unique_together = ("user", "group")
        verbose_name = "用户组成员"
        verbose_name_plural = "用户组成员"


class SysMenu(models.Model):
	class MenuType(models.TextChoices):
		CATALOG = "catalog", "目录"
		MENU = "menu", "菜单"
		BUTTON = "button", "按钮"

	parent = models.ForeignKey(
		"self",
		verbose_name="父级菜单",
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="children",
	)
	menu_name = models.CharField("菜单名称", max_length=64)
	menu_type = models.CharField("菜单类型", max_length=16, choices=MenuType.choices)
	path = models.CharField("路由路径", max_length=255, blank=True)
	component = models.CharField("前端组件", max_length=255, blank=True)
	permission_code = models.CharField("权限编码", max_length=128, unique=True)
	sort = models.PositiveIntegerField("排序", default=0)
	visible = models.BooleanField("是否可见", default=True)
	status = models.CharField("状态", max_length=16, default="active")
	created_at = models.DateTimeField("创建时间", auto_now_add=True)
	updated_at = models.DateTimeField("更新时间", auto_now=True)

	class Meta:
		db_table = "sys_menu"
		ordering = ["sort", "id"]
		verbose_name = "菜单"
		verbose_name_plural = "菜单"

	def __str__(self):
		return self.menu_name


class SysGroupMenu(models.Model):
    group = models.ForeignKey(SysGroup, verbose_name="用户组", on_delete=models.CASCADE)
    menu = models.ForeignKey(SysMenu, verbose_name="菜单", on_delete=models.CASCADE)

    class Meta:
        db_table = "sys_group_menu"
        unique_together = ("group", "menu")
        verbose_name = "用户组菜单权限"
        verbose_name_plural = "用户组菜单权限"
