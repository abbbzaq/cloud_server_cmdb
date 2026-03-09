# 云服务器 CMDB 功能文档（MVP）

## 1. 文档目的
本文档用于说明当前后端已实现的核心功能、角色权限、主要接口能力与使用约定，供产品、前端、测试与运维协同使用。

---

## 2. 系统概览
- 技术栈：Python + Django + Django REST Framework + MySQL
- 管理后台：`/admin/`
- 健康检查：`/healthz`
- API 根路径：
  - ` /api/v1/assets/`（资产域）
  - ` /api/v1/audit/`（审计域）
  - ` /api/v1/iam/`（身份与权限域）

---

## 3. 角色与权限模型
系统角色采用三类：
- 管理员（admin）
- 运维（ops）
- 只读（readonly）

### 3.1 权限策略
- 资产接口：
  - 查询：管理员/运维/只读
  - 新增、修改、删除：管理员/运维
- 审计接口：
  - 查询：管理员/运维/只读
- IAM 接口（用户、用户组、菜单、关系管理）：
  - 仅管理员

### 3.2 角色来源
角色通过 `sys_group` + `sys_user_group` 关联判定。
默认角色组名称：`管理员`、`运维`、`只读`。

---

## 4. 统一接口规范

### 4.1 认证方式
- JWT（Bearer Token）
- SessionAuthentication
- BasicAuthentication

### 4.2 分页
- 默认分页器：PageNumberPagination
- 默认每页：20

### 4.3 统一返回格式
成功：
```json
{
  "code": 201,
  "msg": "success",
  "data": {}
}
```

失败：
```json
{
  "code": 501,
  "msg": "error message",
  "data": {}
}
```

---

## 5. 功能模块说明

## 5.1 资产管理（assets）
### 5.1.1 云账号管理
资源：`accounts`
能力：新增、列表、详情、修改、删除

### 5.1.2 云实例管理
资源：`instances`
能力：新增、列表、详情、修改、删除

### 5.1.3 资产检索能力
实例列表支持过滤参数：
- `provider`
- `account_id`
- `region`
- `status`
- `owner`
- `env`
- `tag_key`
- `tag_value`

### 5.1.4 关系视图能力
- `GET /api/v1/assets/instances/{id}/relations/`
- 返回实例与关联的账号、云盘、网络、标签数据

### 5.1.5 基础告警能力
- `GET /api/v1/assets/instances/alerts/`
- 返回：
  - 无负责人实例统计与样本
  - 缺关键标签实例统计与样本（按 `env/business_unit/owner/cost_center/service_name` 五个必填标签校验）
  - 高危端口暴露实例统计与样本

### 5.1.6 变更审计写入
资产创建/更新/删除时自动写入 `change_log`。

---

## 5.2 审计日志（audit）
资源：`change-logs`
能力：列表、详情

支持过滤参数：
- `resource_type`
- `resource_id`
- `operator`
- `field`
- `start_time`
- `end_time`

可用于按资源、时间、操作者、字段追溯变更。

---

## 5.3 身份与权限（iam）

### 5.3.1 用户资料管理
资源：`users`
能力：新增、列表、详情、修改、删除

### 5.3.2 用户组管理
资源：`groups`
能力：新增、列表、详情、修改、删除

### 5.3.3 菜单管理
资源：`menus`
能力：新增、列表、详情、修改、删除

### 5.3.4 用户-用户组关系管理
资源：`user-groups`
能力：新增、列表、详情、修改、删除

### 5.3.5 用户组-菜单关系管理
资源：`group-menus`
能力：新增、列表、详情、修改、删除

### 5.3.6 角色切换接口（管理员专用）
- `POST /api/v1/iam/users/assign-role/`
- 入参：
  - `username`
  - `role`（`admin` / `ops` / `readonly`，兼容中文）
- 行为：
  - 自动移除旧角色组映射
  - 绑定新角色组
  - 同步 Django 用户属性（`is_staff`、`is_superuser`）

### 5.3.7 登录与会话接口
- `POST /api/v1/iam/login/`
  - 入参：`username`、`password`
  - 返回当前用户信息、角色列表与 JWT Token（`access`、`refresh`）
- `POST /api/v1/iam/token/refresh/`
  - 入参：`refresh`
  - 返回新的 `access` Token
- `POST /api/v1/iam/logout/`
  - 退出当前会话
- `GET /api/v1/iam/me/`
  - 获取当前登录用户信息

---

## 6. 后端技术方案（新增）

本章节用于承接“云服务器 CMDB 自动化发现、关系建模、变更追踪”的后端落地方案，基于当前 Orion 项目做增量开发。

### 6.1 架构分层

- API 层：`assets/views.py`（参数校验、权限控制、统一响应）
- 服务层：`assets/sync.py`（云资源同步、幂等更新、审计记录）
- 模型层：`assets/models.py` + `auditlog/models.py`
- 调度层：`management command` + 后续可接入 Celery/定时任务平台

### 6.2 同步流程

1. 根据 `provider/account_id/region` 获取云端实例清单。
2. 按 `instance_id` 执行幂等 upsert。
3. 同步标签（新增、更新、删除）。
4. 对云端已不存在但 CMDB 仍存在的实例标记为 `released`。
5. 写入 `change_log`（`source=cloud_sync`）。

### 6.3 已新增后端能力

- 阿里云同步接口：`POST /api/v1/assets/instances/sync/aliyun/`
- 腾讯云同步接口：`POST /api/v1/assets/instances/sync/tencent/`
- UCloud 同步接口：`POST /api/v1/assets/instances/sync/ucloud/`
- 拓扑查询接口：`GET /api/v1/assets/instances/{id}/topology/`
- 定时可调用命令：`python manage.py sync_cloud_instances ...`

---

## 7. 数据库设计（新增）

### 7.1 核心表与职责

1. `cloud_account`
- 云账号维度：`provider`、`account_id`、`project_name`、`auth_ref`、`status`。

2. `cloud_instance`
- 核心 CI：`instance_id`、`name`、`account(FK)`、`region`、`zone`、`instance_type`、`image_id`、`os_type`、`private_ip`、`public_ip`、`status`、`owner`、`env`。

3. `cloud_disk`
- 磁盘 CI，关联 `instance(FK)`。

4. `cloud_network`
- 网络与安全快照：`vpc_id`、`subnet_id`、`security_group_id`、`cidr`、`inbound_rules`、`outbound_rules`，关联 `instance(FK)`。

5. `cloud_tag`
- 标签扩展：`(instance, tag_key)` 唯一，支持动态业务字段。

6. `change_log`
- 变更审计：`resource_type`、`resource_id`、`field`、`old_value`、`new_value`、`operator`、`source`、`changed_at`。

### 7.2 一致性策略

- 不做硬删除，云侧资源消失后置为 `released`。
- `create/update/released` 全量写审计。
- 同步过程使用事务，避免部分写入。

### 7.3 扩展建议（后续）

- `cloud_instance` 增加 `cpu_cores`、`memory_mb`、`expired_at`、`raw_payload(JSON)`。
- 增加通用关系表 `cmdb_relation`，支持 RDS/LB 等新 CI。

---

## 8. 关键代码示例（新增）

### 8.1 云实例同步服务示例

文件：`backend/assets/sync.py`

```python
result = CloudInstanceSyncService.sync_instances(
  provider="aliyun",
  account_id=account_id,
  project_name=project_name,
  auth_ref=auth_ref,
  instances=instances,
  operator="system",
  source="cloud_sync",
)
```

说明：
- 按 `instance_id` 幂等更新。
- 自动对比字段并写入 `change_log`。
- 自动处理 `released` 状态。

### 8.2 关系拓扑查询 API 示例

文件：`backend/assets/views.py`

```python
@api_view(["GET"])
@permission_classes([IsAdminOrOpsWriteElseRead])
def cloud_instance_topology(request, pk):
  # 输出 center + nodes + edges，供前端图组件直接渲染
  ...
```

说明：
- 节点类型含 `instance/account/disk/network/tag`。
- 边关系含 `belongs_to/attached_to/connected_to/has_tag`。

### 8.3 管理命令示例

文件：`backend/assets/management/commands/sync_cloud_instances.py`

腾讯云同步：

```bash
python manage.py sync_cloud_instances --provider tencent --account-id tencent-001 --project-name default --region ap-guangzhou
```

UCloud 同步：

```bash
python manage.py sync_cloud_instances --provider ucloud --account-id ucloud-001 --project-name default --region cn-bj2
```

阿里云 ECS 同步：

```bash
python manage.py sync_cloud_instances --provider aliyun --account-id prod-001 --project-name prod --region cn-hangzhou --access-key-id <AK> --access-key-secret <SK>
```

---

## 9. 分阶段实施与优先级（新增）

### 9.1 第一阶段（MVP）

1. 单云实例同步（轮询）
2. 实例列表与过滤
3. 审计日志闭环（create/update/released）

### 9.2 第二阶段

1. 扩展磁盘/EIP/安全组同步
2. 关系拓扑图可视化
3. 变更追踪与告警联动

### 9.3 第三阶段

1. 多云接入（AWS/腾讯云）
2. 事件驱动同步（消息/变更流）
3. 第三方平台消费 API 强化（监控、发布、自动化）

---

## 10. POST 接口传参格式

以下为当前后端所有 `POST` 接口的请求体 JSON 模板。

### 10.1 资产域（`/api/v1/assets/`）

1. 新增云账号
接口：`POST /api/v1/assets/accounts/`

```json
{
  "provider": "aliyun",
  "account_id": "prod-001",
  "project_name": "default-project",
  "auth_ref": "kms://cmdb-cloud-key",
  "status": "active"
}
```

2. 新增云实例
接口：`POST /api/v1/assets/instances/`

```json
{
  "instance_id": "ins-001",
  "name": "web-01",
  "account_id": 1,
  "region": "ap-guangzhou",
  "zone": "ap-guangzhou-3",
  "instance_type": "S5.MEDIUM4",
  "image_id": "img-xxxxx",
  "os_type": "linux",
  "private_ip": "10.0.0.10",
  "public_ip": "1.2.3.4",
  "status": "running",
  "charge_type": "postpaid",
  "owner": "ops-team",
  "env": "prod"
}
```

说明：`account_id` 为 `cloud_account.id`（整数主键）。
说明：`charge_type` 可选 `postpaid` 或 `prepaid`。

3. 同步阿里云实例
接口：`POST /api/v1/assets/instances/sync/aliyun/`

```json
{
  "account_id": "aliyun-account",
  "project_name": "default-project",
  "auth_ref": "kms://aliyun-ak",
  "region": "cn-hangzhou",
  "access_key_id": "your-ak",
  "access_key_secret": "your-sk"
}
```

4. 同步腾讯云实例
接口：`POST /api/v1/assets/instances/sync/tencent/`

```json
{
  "account_id": "tencent-account",
  "project_name": "default-project",
  "auth_ref": "kms://tencent-secret",
  "region": "ap-guangzhou"
}
```

5. 同步 UCloud 实例
接口：`POST /api/v1/assets/instances/sync/ucloud/`

```json
{
  "account_id": "ucloud-account",
  "project_name": "default-project",
  "auth_ref": "kms://ucloud-secret",
  "region": "cn-bj2"
}
```

### 10.2 身份域（`/api/v1/iam/`）

1. 登录
接口：`POST /api/v1/iam/login/`

```json
{
  "username": "admin",
  "password": "123456"
}
```

2. 刷新 Token
接口：`POST /api/v1/iam/token/refresh/`

```json
{
  "refresh": "<refresh_token>"
}
```

3. 退出登录
接口：`POST /api/v1/iam/logout/`

```json
{}
```

4. 新增系统用户
接口：`POST /api/v1/iam/users/`

方式 A（推荐，自动创建 Django 用户）：

```json
{
  "username": "alice",
  "password": "123456",
  "display_name": "Alice",
  "phone": "13800138000",
  "status": "active"
}
```

方式 B（绑定已有 Django 用户）：

```json
{
  "user_id": 2,
  "display_name": "Alice",
  "phone": "13800138000",
  "status": "active"
}
```

5. 分配角色
接口：`POST /api/v1/iam/users/assign-role/`

```json
{
  "username": "alice",
  "role": "admin"
}
```

说明：`role` 支持 `admin`、`ops`、`readonly`（含中文别名）。

6. 新增用户组
接口：`POST /api/v1/iam/groups/`

```json
{
  "group_name": "运维组",
  "description": "运维团队",
  "status": "active"
}
```

7. 新增菜单
接口：`POST /api/v1/iam/menus/`

```json
{
  "parent_id": null,
  "menu_name": "资产管理",
  "menu_type": "menu",
  "path": "/assets",
  "component": "pages/assets/index",
  "permission_code": "assets:view",
  "sort": 10,
  "visible": true,
  "status": "active"
}
```

说明：`menu_type` 可选 `catalog`、`menu`、`button`。

8. 新增用户组成员关系
接口：`POST /api/v1/iam/user-groups/`

```json
{
  "user": 2,
  "group": 1
}
```

9. 新增用户组菜单关系
接口：`POST /api/v1/iam/group-menus/`

```json
{
  "group": 1,
  "menu": 3
}
```
4. 标签治理与基于标签的高级检索

---

## 10. 权限与安全建议（新增）

- 同步类接口建议仅管理员可执行（生产环境）。
- `auth_ref` 仅保存密钥引用，不保存明文 AK/SK。
- 通过 `source` 字段区分人工操作与系统同步。
- 对外错误信息脱敏，避免泄露云账号凭据。

---

## 11. 初始化与联调支持

### 11.1 角色与测试用户初始化命令
```bash
python manage.py bootstrap_rbac --with-demo-users --password 123456
```

默认测试用户组：
- `管理员`
- `运维`
- `只读`

默认测试用户：
- `admin_user`
- `ops_user`
- `readonly_user`

测试用户与用户组映射：
- `admin_user` -> `管理员`
- `ops_user` -> `运维`
- `readonly_user` -> `只读`

> 建议：仅用于开发联调环境，生产环境必须禁用测试账号并强制改密。

### 11.2 Apifox 联调建议顺序
建议在 Apifox 中配置环境变量：
- `base_url = http://127.0.0.1:8000`

建议测试顺序：
1. 健康检查：`GET {{base_url}}/healthz`
2. 登录：`POST {{base_url}}/api/v1/iam/login/`
   - Body：
   ```json
   {
     "username": "user1",
     "password": "lol.131400"
   }
   ```
3. 当前用户：`GET {{base_url}}/api/v1/iam/me/`
4. 资产列表：`GET {{base_url}}/api/v1/assets/accounts/`
5. 审计列表：`GET {{base_url}}/api/v1/audit/change-logs/`
6. 退出：`POST {{base_url}}/api/v1/iam/logout/`

常见问题：
- 返回 `405`：通常是 URL 使用了列表路径却调用了 `PUT/DELETE`，请改为带主键的详情路径。
  - 例如：更新云账号应使用 `PUT /api/v1/assets/accounts/{id}/`。
- 返回权限错误：确认当前用户已绑定角色（`管理员`/`运维`/`只读`）。

---

## 12. 管理后台能力
- 后台地址：`/admin/`
- 已完成：
  - 模型中文名称与字段中文提示
  - 后台列表展示、搜索、筛选
  - 默认排序与分页优化
  - 后台中文站点标题

---

## 13. MVP 完成度说明
按当前代码与路由实际可用能力评估，MVP 后端完成度约 **85%**。

### 13.1 已完成（可联调）
- 资产域（assets）
  - 云账号 CRUD
  - 云实例 CRUD
  - 实例多条件筛选（provider/account_id/region/status/owner/env/tag_key/tag_value）
  - 实例关系视图（relations）
  - 基础告警统计（alerts）
  - 资产变更自动写审计日志
- 审计域（audit）
  - 审计日志列表/详情
  - 按资源、操作者、字段、时间区间过滤
- 身份域（iam）
  - 用户、用户组、菜单、关系管理 CRUD
  - 角色分配接口（assign-role）
  - 登录/退出/当前用户接口（login/logout/me）
  - JWT 刷新接口（token/refresh）
  - 新用户登录兼容：若仅有 Django 用户账号，会在首次登录自动补齐用户资料与只读角色
- 统一能力
  - 统一返回结构（code/msg/data）
  - 统一异常包装
  - 后台中文化配置与健康检查接口

### 13.2 已实现但待增强
- 权限粒度目前到角色级（admin/ops/readonly），菜单/按钮级权限码尚未落地。
- 鉴权方式已支持 JWT + Session/Basic；JWT 黑名单/主动失效机制尚未接入。

### 13.3 当前未纳入运行范围
- `costs`、`governance` 模块已从 `INSTALLED_APPS` 与主路由移除，当前不提供 API 服务。

### 13.4 后续迭代建议
- 更细粒度菜单/按钮权限校验
- 差异处理工作流与审批流
- 成本统计报表 API（重新规划并接入运行）
- 告警任务调度与通知通道
