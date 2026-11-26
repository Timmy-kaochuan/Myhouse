# 重型燃机集成设计平台 — Windows 离线部署说明

本包为**全离线部署包**：目标电脑无需联网、无需 Node.js、无需数据库服务器（默认 SQLite）。

## 包内容

| 目录/文件 | 说明 |
|-----------|------|
| `app/` | FastAPI 后端源码（模型/CRUD/接口） |
| `alembic/` + `alembic.ini` | 数据库迁移脚本 |
| `frontend/dist/` | 已构建好的前端页面（由后端直接托管，无需 Node） |
| `wheels/` | Python 依赖离线安装包（Windows x64，覆盖 Python 3.10 ~ 3.13） |
| `requirements.txt` | 依赖版本清单（与开发环境一致） |
| `install.bat` | 一键安装：建虚拟环境 → 离线装依赖 → 初始化数据库 |
| `start.bat` | 一键启动：起服务（8000 端口）并自动打开浏览器 |

## 部署步骤（目标电脑）

1. 将整个文件夹从 U 盘拷贝到目标电脑任意目录（**路径不要包含中文或空格**，如 `D:\ai_platform`）
2. 双击 `install.bat`，等待出现"安装完成"
3. 双击 `start.bat`，浏览器自动打开 `http://127.0.0.1:8000`
4. 局域网内其他电脑访问：`http://<本机IP>:8000`（Windows 防火墙首次会弹窗，选择"允许访问"）

## 首次使用：创建用户

算例管理页新建算例时需要选择"创建人"，因此先创建用户（Windows 10+ 自带 curl，在项目目录开命令行执行）：

```bat
curl -X POST http://127.0.0.1:8000/api/users -H "Content-Type: application/json" -d "{\"email\":\"admin@gtes.local\",\"display_name\":\"管理员\",\"role\":\"admin\"}"
```

## 数据说明

- 默认使用 SQLite，数据库文件为项目目录下的 `ai_platform.db`，**备份该文件即备份全部数据**
- 所有时间均为 UTC
- 网格/结果/模型权重等大文件只存 MinIO 对象 key（字符串），当前 MVP 不依赖 MinIO 服务

## 切换 PostgreSQL（可选）

如需连接内网 PostgreSQL，启动前设置环境变量（依赖包已含 asyncpg）：

```bat
set DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/ai_platform
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 常见问题

| 问题 | 处理 |
|------|------|
| install.bat 报"未找到 Python" | 确认已装 Python 3.10~3.13 并勾选"加入 PATH"，或重装时勾选 |
| 依赖安装失败 | 运行 `.venv\Scripts\python --version` 确认版本在 3.10~3.13 之间 |
| 端口被占用 | 编辑 start.bat 把 `--port 8000` 改成其他端口 |
| 页面打不开 | 确认命令行窗口显示 `Uvicorn running on http://0.0.0.0:8000` |
