# ai_platform

AI 平台后端服务，基于 Python + FastAPI，异步 SQLAlchemy 2.0 + Alembic。

## 环境要求

- Python >= 3.10

## 安装

```bash
cd ai_platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 配置

通过环境变量配置，默认值可直接本地开发：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `AI Platform` | 应用名 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./ai_platform.db` | 数据库连接串 |
| `SQL_ECHO` | `false` | 是否打印 SQL |

生产环境示例：

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/ai_platform"
```

## 数据库迁移

```bash
alembic upgrade head      # 应用最新迁移
alembic revision --autogenerate -m "describe change"  # 模型变更后生成迁移
alembic downgrade -1      # 回滚一步
```

## 运行

```bash
uvicorn app.main:app --reload
```

- http://127.0.0.1:8000/health —— 服务存活检查
- http://127.0.0.1:8000/health/db —— 数据库连通性检查
- http://127.0.0.1:8000/docs —— API 文档

## 测试

```bash
pytest
```

## 目录结构

```
ai_platform/
├── app/
│   ├── api/routes.py      # 路由定义
│   ├── core/config.py     # 配置
│   ├── db/
│   │   ├── base.py        # ORM 基类
│   │   └── session.py     # 异步引擎、会话、依赖
│   ├── models/user.py     # 示例模型
│   └── main.py            # 应用入口
├── alembic/
│   ├── env.py             # 迁移环境（异步）
│   └── versions/          # 迁移脚本
├── tests/
├── alembic.ini
└── pyproject.toml
```
