import os

from django.core.management.base import BaseCommand, CommandError

from assets.sync import (
    AliyunEcsInstanceProvider,
    CloudInstanceSyncService,
    MockTencentCloudInstanceProvider,
    MockUcloudInstanceProvider,
    ProviderConfigError,
)


class Command(BaseCommand):
    help = "同步云服务器实例到CMDB（支持 aliyun/tencent/ucloud）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            default="aliyun",
            choices=["aliyun", "tencent", "ucloud"],
            help="同步来源",
        )
        parser.add_argument("--account-id", required=True, help="云账号ID")
        parser.add_argument("--project-name", default="default-project", help="项目名称")
        parser.add_argument("--auth-ref", default="kms://cmdb-cloud-key", help="凭证引用")
        parser.add_argument("--region", default="cn-hangzhou", help="区域")
        parser.add_argument("--operator", default="system", help="操作人")
        parser.add_argument("--access-key-id", default="", help="阿里云AK，可不传并走环境变量")
        parser.add_argument("--access-key-secret", default="", help="阿里云SK，可不传并走环境变量")

    def handle(self, *args, **options):
        provider = options["provider"]
        account_id = options["account_id"]
        project_name = options["project_name"]
        auth_ref = options["auth_ref"]
        region = options["region"]
        operator = options["operator"]

        if provider == "tencent":
            cloud_provider = MockTencentCloudInstanceProvider()
            instances = cloud_provider.list_instances(account_id=account_id, region=region)
            result = CloudInstanceSyncService.sync_instances(
                provider="tencent",
                account_id=account_id,
                project_name=project_name,
                auth_ref=auth_ref,
                instances=instances,
                operator=operator,
                source="cloud_sync",
            )
            self.stdout.write(self.style.SUCCESS(f"同步完成: {result}"))
            return

        if provider == "ucloud":
            cloud_provider = MockUcloudInstanceProvider()
            instances = cloud_provider.list_instances(account_id=account_id, region=region)
            result = CloudInstanceSyncService.sync_instances(
                provider="ucloud",
                account_id=account_id,
                project_name=project_name,
                auth_ref=auth_ref,
                instances=instances,
                operator=operator,
                source="cloud_sync",
            )
            self.stdout.write(self.style.SUCCESS(f"同步完成: {result}"))
            return

        access_key_id = options["access_key_id"] or os.getenv("ALIYUN_ACCESS_KEY_ID", "")
        access_key_secret = options["access_key_secret"] or os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")

        try:
            cloud_provider = AliyunEcsInstanceProvider(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
            )
            instances = cloud_provider.list_instances(account_id=account_id, region=region)
            result = CloudInstanceSyncService.sync_instances(
                provider="aliyun",
                account_id=account_id,
                project_name=project_name,
                auth_ref=auth_ref,
                instances=instances,
                operator=operator,
                source="cloud_sync",
            )
            self.stdout.write(self.style.SUCCESS(f"同步完成: {result}"))
        except ProviderConfigError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"同步失败: {exc}") from exc
