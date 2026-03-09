# Orion 云服务器 CMDB（MVP）

一个面向云服务器资产管理的 CMDB 项目，采用 Django + DRF 后端与 React + shadcn/ui 前端。

## 技术栈

### 后端

- Python 3.11
- Django 4.2.28
- Django REST Framework 3.16.1
- MySQL 8.0

### 前端

- React 18 + TypeScript
- Vite 5
- Tailwind CSS
- shadcn/ui（以组件模式集成）

## 目录结构

```text
Orion/
├── backend/
│   ├── cmdb_backend/
│   ├── assets/
│   ├── auditlog/
│   ├── iam/
│   ├── costs/
│   ├── governance/
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/ui/
│   │   ├── lib/
│   │   ├── styles/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── tailwind.config.ts
├── docker-compose.yml
├── docs/
│   ├── architecture/
│   ├── product/
│   ├── standards/
│   └── README.md
└── README.md
```

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认开发端口：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`

## Docker Compose 部署

项目已提供一键编排：`frontend + backend + mysql`。

```bash
docker compose up -d --build
```

访问地址：

- 前端：`http://127.0.0.1:3000`
- 后端 API：`http://127.0.0.1:8001`
- 管理后台：`http://127.0.0.1:3000/admin/`（由前端 Nginx 反向代理）

停止服务：

```bash
docker compose down
```

清理数据卷（会删除 MySQL 数据）：

```bash
docker compose down -v
```

## 接口基线

- 健康检查：`/healthz`
- 资产域：`/api/v1/assets/`
- 审计域：`/api/v1/audit/`
- 身份域：`/api/v1/iam/`

## 前端说明（React + shadcn/ui）

- 已初始化 `shadcn/ui` 常用基础能力：`cn` 工具函数与 `Button` 组件。
- 样例入口页面在 `frontend/src/App.tsx`，可直接扩展路由、状态管理与 API 请求层。
- 路径别名 `@` 已配置到 `frontend/src`。

## 角色与权限（后端）

- `admin`：全量权限
- `ops`：资产读写 + 审计查询
- `readonly`：只读查询

可通过以下命令初始化默认角色并创建测试账号：

```bash
cd backend
python manage.py bootstrap_rbac --with-demo-users --password 123456
```

## 质量检查

后端测试：

```bash
cd backend
python manage.py test
```

前端构建检查：

```bash
cd frontend
npm run build
```

Compose 配置校验：

```bash
docker compose config
```

## 云资源同步（后端）

同步（腾讯云/UCloud Mock + 阿里云真实接口）：

```bash
cd backend
python manage.py sync_cloud_instances --provider tencent --account-id tencent-001 --project-name default --region ap-guangzhou
python manage.py sync_cloud_instances --provider ucloud --account-id ucloud-001 --project-name default --region cn-bj2
```

真实阿里云同步（ECS）：

```bash
cd backend
export ALIYUN_ACCESS_KEY_ID=your-ak
export ALIYUN_ACCESS_KEY_SECRET=your-sk
python manage.py sync_cloud_instances --provider aliyun --account-id prod-001 --project-name prod --region cn-hangzhou
```

HTTP 接口：

- `POST /api/v1/assets/instances/sync/aliyun/`
- `POST /api/v1/assets/instances/sync/tencent/`
- `POST /api/v1/assets/instances/sync/ucloud/`
- `GET /api/v1/assets/instances/{id}/topology/`

## 开发规范

请阅读 `docs/standards/DEVELOPMENT.md`，包含分支策略、代码组织、提交规范、联调与发布检查清单。

## 相关文档

- `docs/README.md`
- `docs/architecture/cloud_server_cmdb_design.md`
- `docs/product/cloud_server_cmdb_function_doc.md`
- `docs/standards/COMMIT_CONVENTION.md`
