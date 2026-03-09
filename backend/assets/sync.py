from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from django.db import transaction

from auditlog.models import ChangeLog

from .models import CloudAccount, CloudInstance, CloudTag


@dataclass
class InstancePayload:
    instance_id: str
    name: str
    region: str
    zone: str = ""
    instance_type: str = ""
    image_id: str = ""
    os_type: str = ""
    private_ip: str = ""
    public_ip: str = ""
    status: str = "running"
    owner: str = ""
    env: str = "dev"
    tags: dict[str, str] = field(default_factory=dict)


class MockTencentCloudInstanceProvider:
    """腾讯云 CVM 的示例 provider。"""

    def list_instances(self, account_id: str, region: str) -> list[InstancePayload]:
        return [
            InstancePayload(
                instance_id=f"ins-{account_id}-001",
                name="tencent-web-01",
                region=region,
                zone=f"{region}-1",
                instance_type="S5.MEDIUM4",
                image_id="img-centos7",
                os_type="linux",
                private_ip="10.10.1.11",
                public_ip="",
                status="running",
                owner="ops-team",
                env="prod",
                tags={"service_name": "web", "env": "prod", "provider": "tencent"},
            ),
            InstancePayload(
                instance_id=f"ins-{account_id}-002",
                name="tencent-job-01",
                region=region,
                zone=f"{region}-2",
                instance_type="SA2.MEDIUM4",
                image_id="img-ubuntu2204",
                os_type="linux",
                private_ip="10.10.2.21",
                public_ip="",
                status="stopped",
                owner="ops-team",
                env="test",
                tags={"service_name": "job", "env": "test", "provider": "tencent"},
            ),
        ]


class MockUcloudInstanceProvider:
    """UCloud UHost 的示例 provider。"""

    def list_instances(self, account_id: str, region: str) -> list[InstancePayload]:
        return [
            InstancePayload(
                instance_id=f"uhost-{account_id}-001",
                name="ucloud-api-01",
                region=region,
                zone=f"{region}-01",
                instance_type="n-basic-2",
                image_id="uimage-centos-7",
                os_type="linux",
                private_ip="10.20.1.31",
                public_ip="",
                status="running",
                owner="ops-team",
                env="prod",
                tags={"service_name": "api", "env": "prod", "provider": "ucloud"},
            ),
            InstancePayload(
                instance_id=f"uhost-{account_id}-002",
                name="ucloud-batch-01",
                region=region,
                zone=f"{region}-02",
                instance_type="n-standard-2",
                image_id="uimage-ubuntu-22",
                os_type="linux",
                private_ip="10.20.2.41",
                public_ip="",
                status="stopped",
                owner="ops-team",
                env="dev",
                tags={"service_name": "batch", "env": "dev", "provider": "ucloud"},
            ),
        ]


class ProviderConfigError(Exception):
    pass


class AliyunEcsInstanceProvider:
    """Aliyun ECS provider based on aliyun-python-sdk-ecs."""

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = (access_key_id or "").strip()
        self.access_key_secret = (access_key_secret or "").strip()
        if not self.access_key_id or not self.access_key_secret:
            raise ProviderConfigError("阿里云 AccessKey 配置缺失")

    def list_instances(self, account_id: str, region: str) -> list[InstancePayload]:
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
        except ImportError as exc:
            raise ProviderConfigError(
                "缺少阿里云SDK依赖，请安装 aliyun-python-sdk-core 和 aliyun-python-sdk-ecs"
            ) from exc

        client = AcsClient(self.access_key_id, self.access_key_secret, region)
        request = DescribeInstancesRequest()
        request.set_accept_format("json")
        request.set_PageSize(100)

        page_number = 1
        items: list[dict] = []
        total_count = 0
        while True:
            request.set_PageNumber(page_number)
            response = client.do_action_with_exception(request)
            payload = json.loads(response)
            total_count = int(payload.get("TotalCount", 0))
            page_items = payload.get("Instances", {}).get("Instance", [])
            items.extend(page_items)
            if len(items) >= total_count or not page_items:
                break
            page_number += 1

        result: list[InstancePayload] = []
        for item in items:
            private_ips = item.get("VpcAttributes", {}).get("PrivateIpAddress", {}).get("IpAddress", [])
            public_ips = item.get("PublicIpAddress", {}).get("IpAddress", [])
            tags = {
                tag.get("TagKey", ""): tag.get("TagValue", "")
                for tag in item.get("Tags", {}).get("Tag", [])
                if tag.get("TagKey")
            }

            result.append(
                InstancePayload(
                    instance_id=item.get("InstanceId", ""),
                    name=item.get("InstanceName") or item.get("HostName") or item.get("InstanceId", ""),
                    region=item.get("RegionId", region),
                    zone=item.get("ZoneId", ""),
                    instance_type=item.get("InstanceType", ""),
                    image_id=item.get("ImageId", ""),
                    os_type=item.get("OSType", ""),
                    private_ip=private_ips[0] if private_ips else "",
                    public_ip=public_ips[0] if public_ips else "",
                    status=(item.get("Status", "") or "").lower(),
                    owner=tags.get("owner", ""),
                    env=tags.get("env", "dev"),
                    tags=tags,
                )
            )
        return result


class CloudInstanceSyncService:
    @staticmethod
    @transaction.atomic
    def sync_instances(
        *,
        provider: str,
        account_id: str,
        project_name: str,
        auth_ref: str,
        instances: Iterable[InstancePayload],
        operator: str = "system",
        source: str = "cloud_sync",
    ) -> dict:
        account, _ = CloudAccount.objects.get_or_create(
            provider=provider,
            account_id=account_id,
            project_name=project_name,
            defaults={"auth_ref": auth_ref, "status": "active"},
        )

        created = 0
        updated = 0
        seen_instance_ids: set[str] = set()
        change_logs: list[ChangeLog] = []

        for item in instances:
            seen_instance_ids.add(item.instance_id)
            obj, was_created = CloudInstance.objects.get_or_create(
                instance_id=item.instance_id,
                defaults={
                    "name": item.name,
                    "account": account,
                    "region": item.region,
                    "zone": item.zone,
                    "instance_type": item.instance_type,
                    "image_id": item.image_id,
                    "os_type": item.os_type,
                    "private_ip": item.private_ip,
                    "public_ip": item.public_ip,
                    "status": item.status,
                    "owner": item.owner,
                    "env": item.env,
                },
            )

            if was_created:
                created += 1
                change_logs.append(
                    ChangeLog(
                        resource_type="cloud_instance",
                        resource_id=item.instance_id,
                        field="create",
                        old_value="",
                        new_value=item.name,
                        operator=operator,
                        source=source,
                    )
                )
            else:
                before = {
                    "name": obj.name,
                    "region": obj.region,
                    "zone": obj.zone,
                    "instance_type": obj.instance_type,
                    "image_id": obj.image_id,
                    "os_type": obj.os_type,
                    "private_ip": obj.private_ip,
                    "public_ip": obj.public_ip,
                    "status": obj.status,
                    "owner": obj.owner,
                    "env": obj.env,
                    "account_id": obj.account_id,
                }

                obj.name = item.name
                obj.account = account
                obj.region = item.region
                obj.zone = item.zone
                obj.instance_type = item.instance_type
                obj.image_id = item.image_id
                obj.os_type = item.os_type
                obj.private_ip = item.private_ip
                obj.public_ip = item.public_ip
                obj.status = item.status
                obj.owner = item.owner
                obj.env = item.env
                obj.save()

                after = {
                    "name": obj.name,
                    "region": obj.region,
                    "zone": obj.zone,
                    "instance_type": obj.instance_type,
                    "image_id": obj.image_id,
                    "os_type": obj.os_type,
                    "private_ip": obj.private_ip,
                    "public_ip": obj.public_ip,
                    "status": obj.status,
                    "owner": obj.owner,
                    "env": obj.env,
                    "account_id": obj.account_id,
                }

                changed_fields = [field for field in before if before[field] != after[field]]
                if changed_fields:
                    updated += 1
                    for field in changed_fields:
                        change_logs.append(
                            ChangeLog(
                                resource_type="cloud_instance",
                                resource_id=item.instance_id,
                                field=field,
                                old_value=str(before[field]),
                                new_value=str(after[field]),
                                operator=operator,
                                source=source,
                            )
                        )

            CloudTag.objects.filter(instance=obj).exclude(tag_key__in=item.tags.keys()).delete()
            for tag_key, tag_value in item.tags.items():
                CloudTag.objects.update_or_create(
                    instance=obj,
                    tag_key=tag_key,
                    defaults={"tag_value": tag_value},
                )

        released_qs = CloudInstance.objects.filter(account=account).exclude(instance_id__in=seen_instance_ids)
        released_count = released_qs.exclude(status="released").count()
        if released_count:
            for instance in released_qs.exclude(status="released"):
                change_logs.append(
                    ChangeLog(
                        resource_type="cloud_instance",
                        resource_id=instance.instance_id,
                        field="status",
                        old_value=instance.status,
                        new_value="released",
                        operator=operator,
                        source=source,
                    )
                )
            released_qs.update(status="released")

        if change_logs:
            ChangeLog.objects.bulk_create(change_logs)

        return {
            "provider": provider,
            "account_id": account_id,
            "project_name": project_name,
            "created": created,
            "updated": updated,
            "released": released_count,
            "total_seen": len(seen_instance_ids),
        }
