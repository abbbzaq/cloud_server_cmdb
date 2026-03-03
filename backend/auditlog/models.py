from django.db import models


class ChangeLog(models.Model):
    resource_type = models.CharField("资源类型", max_length=64)
    resource_id = models.CharField("资源ID", max_length=128)
    field = models.CharField("变更字段", max_length=64)
    old_value = models.TextField("旧值", blank=True)
    new_value = models.TextField("新值", blank=True)
    operator = models.CharField("操作人", max_length=64)
    source = models.CharField("来源", max_length=32, default="manual")
    changed_at = models.DateTimeField("变更时间", auto_now_add=True)

    class Meta:
        db_table = "change_log"
        verbose_name = "变更日志"
        verbose_name_plural = "变更日志"
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["operator"]),
            models.Index(fields=["changed_at"]),
        ]

    def __str__(self):
        return f"{self.resource_type}:{self.resource_id}:{self.field}"
