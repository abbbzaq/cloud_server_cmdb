from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        abstract = True


class CloudAccount(TimeStampedModel):
    provider = models.CharField("云厂商", max_length=32)
    account_id = models.CharField("云账号ID", max_length=128)
    project_name = models.CharField("项目名称", max_length=128)
    auth_ref = models.CharField("凭证引用", max_length=255)
    status = models.CharField("状态", max_length=32, default="active")

    class Meta:
        db_table = "cloud_account"
        unique_together = ("provider", "account_id", "project_name")
        verbose_name = "云账号"
        verbose_name_plural = "云账号"

    def __str__(self):
        return f"{self.provider}:{self.account_id}:{self.project_name}"


class CloudInstance(TimeStampedModel):
	class ChargeType(models.TextChoices):
		POSTPAID = "postpaid", "按量"
		PREPAID = "prepaid", "包年包月"

	instance_id = models.CharField("实例ID", max_length=128, unique=True)
	name = models.CharField("实例名称", max_length=128)
	account = models.ForeignKey(
		CloudAccount,
		verbose_name="所属账号",
		on_delete=models.PROTECT,
		related_name="instances",
	)
	region = models.CharField("地域", max_length=64)
	zone = models.CharField("可用区", max_length=64, blank=True)
	instance_type = models.CharField("实例规格", max_length=64)
	image_id = models.CharField("镜像ID", max_length=128, blank=True)
	os_type = models.CharField("操作系统", max_length=64, blank=True)
	private_ip = models.CharField("私网IP", max_length=64, blank=True)
	public_ip = models.CharField("公网IP", max_length=64, blank=True)
	status = models.CharField("状态", max_length=32)
	charge_type = models.CharField(
		"计费方式",
		max_length=32,
		choices=ChargeType.choices,
		default=ChargeType.POSTPAID,
	)
	owner = models.CharField("负责人", max_length=64, blank=True)
	env = models.CharField("环境", max_length=16, default="dev")

	class Meta:
		db_table = "cloud_instance"
		verbose_name = "云实例"
		verbose_name_plural = "云实例"
		indexes = [
			models.Index(fields=["region"]),
			models.Index(fields=["status"]),
			models.Index(fields=["owner"]),
			models.Index(fields=["env"]),
		]

	def __str__(self):
		return self.instance_id


class CloudDisk(TimeStampedModel):
    disk_id = models.CharField("云盘ID", max_length=128, unique=True)
    disk_type = models.CharField("云盘类型", max_length=64)
    size_gb = models.PositiveIntegerField("容量(GB)")
    encrypted = models.BooleanField("是否加密", default=False)
    instance = models.ForeignKey(
        CloudInstance,
        verbose_name="挂载实例",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disks",
    )
    status = models.CharField("状态", max_length=32)

    class Meta:
        db_table = "cloud_disk"
        verbose_name = "云盘"
        verbose_name_plural = "云盘"

    def __str__(self):
        return self.disk_id


class CloudNetwork(models.Model):
	vpc_id = models.CharField("VPC ID", max_length=128)
	subnet_id = models.CharField("子网ID", max_length=128)
	security_group_id = models.CharField("安全组ID", max_length=128)
	cidr = models.CharField("网段", max_length=64)
	inbound_rules = models.JSONField("入站规则", default=list)
	outbound_rules = models.JSONField("出站规则", default=list)
	instance = models.ForeignKey(
		CloudInstance,
		verbose_name="关联实例",
		on_delete=models.CASCADE,
		related_name="networks",
	)
	updated_at = models.DateTimeField("更新时间", auto_now=True)

	class Meta:
		db_table = "cloud_network"
		verbose_name = "网络与安全"
		verbose_name_plural = "网络与安全"


class CloudTag(models.Model):
	instance = models.ForeignKey(
		CloudInstance,
		verbose_name="关联实例",
		on_delete=models.CASCADE,
		related_name="tags",
	)
	tag_key = models.CharField("标签键", max_length=64)
	tag_value = models.CharField("标签值", max_length=255)

	class Meta:
		db_table = "cloud_tag"
		unique_together = ("instance", "tag_key")
		verbose_name = "实例标签"
		verbose_name_plural = "实例标签"

	def __str__(self):
		return f"{self.tag_key}={self.tag_value}"
