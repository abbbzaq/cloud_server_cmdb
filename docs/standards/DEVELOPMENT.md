# Orion 开发规范

## 1. 分支与协作

- `main` 保持可发布状态。
- 功能开发使用 `feature/<name>` 分支。
- 修复使用 `fix/<name>` 分支。
- 合并前确保完成自测与文档同步。

## 2. 提交规范

提交格式：

```text
<type>: <subject>
```

`type` 取值：

- `feat` 新功能
- `fix` 缺陷修复
- `docs` 文档更新
- `refactor` 重构
- `style` 格式调整
- `test` 测试相关
- `chore` 构建与配置

示例：

- `feat: 新增前端容器化部署配置`
- `fix: 修复资产接口权限判定`

## 3. 后端开发约定（Django + DRF）

- 新接口统一放在对应 app 的 `urls.py` 与 `views.py`。
- 权限控制必须显式声明 `@permission_classes`。
- 数据校验统一通过 `serializers.py` 完成。
- 资源变更接口需要考虑审计日志写入。
- 保持统一响应结构，不引入新的返回格式。

## 4. 前端开发约定（React + shadcn/ui）

- 页面放在 `frontend/src/pages`。
- 复用组件优先放在 `frontend/src/components`，基础 UI 放在 `frontend/src/components/ui`。
- 工具函数统一放在 `frontend/src/lib`。
- 样式通过 Tailwind 管理，避免零散内联样式。
- 组件命名使用 PascalCase，hooks 使用 `useXxx`。

## 5. 本地联调约定

- 前端开发默认请求后端 `http://127.0.0.1:8000`。
- 使用 Docker Compose 联调时，通过 `http://127.0.0.1:3000` 访问统一入口。
- 每次接口变更需同步更新 README 或功能文档。

## 6. 提交前检查清单

- 后端：`python manage.py test`
- 前端：`npm run build`
- 编排：`docker compose config`
- 文档：README 与变更内容一致

## 7. 禁止事项

- 禁止提交密钥、密码、私有证书。
- 禁止未经验证直接修改生产配置。
- 禁止绕过权限逻辑直接在视图中写死角色判断。
