# ai_platform

AI 平台后端服务，基于 Python + FastAPI。

## 环境要求

- Python >= 3.10

## 安装

```bash
cd ai_platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 运行

```bash
uvicorn app.main:app --reload
```

访问 http://127.0.0.1:8000/health 检查服务状态，API 文档在 http://127.0.0.1:8000/docs。

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
│   └── main.py            # 应用入口
├── tests/
│   └── test_health.py
└── pyproject.toml
```
