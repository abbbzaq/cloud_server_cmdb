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
  - 返回当前用户信息与角色列表
- `POST /api/v1/iam/logout/`
  - 退出当前会话
- `GET /api/v1/iam/me/`
  - 获取当前登录用户信息

---

## 6. 初始化与联调支持

### 6.1 角色与测试用户初始化命令
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

### 6.2 Apifox 联调建议顺序
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

## 7. 管理后台能力
- 后台地址：`/admin/`
- 已完成：
  - 模型中文名称与字段中文提示
  - 后台列表展示、搜索、筛选
  - 默认排序与分页优化
  - 后台中文站点标题

---

## 8. MVP 完成度说明
已覆盖设计说明书中的核心后端能力：
- 资产主数据 CRUD
- 资产检索与关系视图
- 审计追踪查询
- 用户/用户组/菜单管理
- 基础角色权限控制

待后续迭代（建议）：
- Token/JWT 认证（当前已支持 Session/Basic 与登录会话接口）
- 更细粒度菜单权限码校验（按钮级）
- 差异处理工作流与审批流
- 成本统计报表 API
- 告警任务调度与通知通道
