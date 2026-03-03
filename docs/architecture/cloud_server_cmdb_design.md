# 云服务器 CMDB 设计思路（MVP）

## 1. 目标定位
- 管理云服务器全生命周期：创建、变更、扩缩容、回收。
- 打通三条主线：
  - 资源线：实例、磁盘、网络、安全组
  - 成本线：规格、时长
  - 责任线：业务线、负责人、运维团队
- 先实现“可追踪、可审计、可对账”，后续再扩展自动化能力。

## 2. 核心数据模型

### 2.1 云账号与项目（cloud_account）
建议字段：
- id
- provider（阿里云/腾讯云/AWS 等）
- account_id
- project_name
- auth_ref（凭证引用，不落明文）
- status
- created_at
- updated_at

### 2.2 云服务器实例（cloud_instance）
建议字段：
- id
- instance_id（云厂商实例唯一标识）
- name
- account_id
- region
- zone
- instance_type
- image_id
- os_type
- private_ip
- public_ip
- status
- charge_type（按量/包年包月）
- owner
- env（dev/test/prod）
- created_at
- updated_at

### 2.3 云盘（cloud_disk）
建议字段：
- id
- disk_id
- disk_type
- size_gb
- encrypted
- instance_id
- status
- created_at
- updated_at

### 2.4 网络与安全（cloud_network）
建议字段：
- id
- vpc_id
- subnet_id
- security_group_id
- cidr
- inbound_rules
- outbound_rules
- instance_id
- updated_at

### 2.5 标签与归属（cloud_tag）
建议字段：
- id
- instance_id
- tag_key
- tag_value

关键标签建议统一：
- env
- business_unit
- owner
- cost_center
- service_name

### 2.6 变更审计（change_log）
建议字段：
- id
- resource_type
- resource_id
- field
- old_value
- new_value
- operator
- source（api_sync/manual/workflow）
- changed_at

### 2.7 用户管理（sys_user）
建议字段：
- id
- username
- display_name
- email
- phone
- status（active/inactive）
- last_login_at
- created_at
- updated_at

### 2.8 用户组管理（sys_group）
建议字段：
- id
- group_name
- description
- status
- created_at
- updated_at

关系表建议：
- `sys_user_group`（user_id, group_id）

### 2.9 菜单管理（sys_menu）
建议字段：
- id
- parent_id
- menu_name
- menu_type（catalog/menu/button）
- path
- component
- permission_code
- sort
- visible
- status
- created_at
- updated_at

关系表建议：
- `sys_group_menu`（group_id, menu_id）

## 3. 关键流程设计

### 3.1 资产发现与同步
- 定时任务拉取云 API（例如 ECS/CVM/EC2）。
- 以 `instance_id` 为主键做增量对账。
- 同步策略：
  - 新增资源：自动入库
  - 属性变更：更新并写审计日志
  - 云上删除：标记“待确认下线”而非直接删除

### 3.2 差异处理机制
- 将“CMDB存在但云上不存在”的资源放入差异队列。
- 支持人工确认：
  - 误报恢复
  - 确认下线
- 对关键字段变更（IP、规格、所属人）触发通知。

### 3.3 生命周期管理
建议状态流转：
- 申请中 -> 运行中 -> 变更中 -> 待回收 -> 已回收

要求：
- 每次状态流转必须有操作者和时间。
- 高风险动作（重建、下线）需审批记录。

## 4. 系统功能（最小可用）
- 资产检索：按云厂商、账号、Region、标签、负责人、状态过滤。
- 关系视图：实例 ↔ 云盘 ↔ VPC/子网 ↔ 安全组。
- 审计查询：按资源、时间、操作者、字段查看变更历史。
- 用户管理：新增/禁用用户，维护用户基础信息。
- 用户组管理：维护用户组并绑定用户。
- 菜单管理：维护菜单树并按用户组分配菜单权限。
- 基础告警：
  - 无负责人实例
  - 无关键标签实例
  - 暴露高危端口（如 0.0.0.0/0 + 22/3389）
  - 长期低利用率僵尸实例

## 5. 权限与治理
- 角色建议：管理员、运维、只读。
- 权限边界：
  - 管理员：全量配置与审批
  - 运维：资源维护与变更提交
  - 只读：查询与报表
- 治理规则：
  - 关键标签缺失禁止进入“生产”状态
  - 无负责人资源进入整改清单

## 6. 报表与指标
- 资源规模：按云厂商/Region/业务线统计实例数量。
- 成本统计：按 `cost_center`、`service_name` 聚合月度成本。
- 质量指标：
  - 标签完整率
  - 责任人覆盖率
  - 差异处理及时率
  - 审计可追溯率

## 7. 实施计划（4 周）
### 第 1 周
- 完成数据模型与字段字典
- 完成云 API 只读同步（实例/磁盘/网络）

### 第 2 周
- 完成资产查询页与关系页
- 完成变更审计日志

### 第 3 周
- 完成差异告警与标签治理校验
- 完成基础角色权限
- 完成用户管理、用户组管理、菜单管理

### 第 4 周
- 完成成本报表
- 完成下线审批流程并灰度上线

## 8. 验收口径（MVP）
- 核心云实例可通过 `instance_id` 唯一追踪。
- 关键标签完整率达到 90% 以上。
- 关键实例变更可按人、时间、字段追溯。
- 差异资源可在一个周期内（如 24h）完成处理。

## 9. 当前后端实现进展（对齐本设计）
- 已实现：
  - 资产管理 API（实例/账号）及 CRUD
  - 资产检索过滤（云厂商、账号、Region、标签、负责人、状态、环境）
  - 关系视图 API（实例关联云盘/网络/标签）
  - 审计查询 API（按资源、时间、操作者、字段过滤）
  - 用户管理、用户组管理、菜单管理及关系管理 API
  - 角色权限（管理员/运维/只读）与统一响应结构
- 暂未完成：
  - 报表指标 API（资源规模、成本标签聚合、质量指标）
  - 差异队列与“差异处理及时率”真实口径计算
  - 下线审批流程 API
  - 基于云厂商账单的真实成本金额对账
