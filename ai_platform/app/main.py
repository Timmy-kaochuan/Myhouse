from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.api.routes import router
from app.core.config import settings
from app.db.session import engine

# 前端构建产物目录（frontend/dist）；不存在时仅提供 API（开发模式走 vite dev 代理）
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

# 路由挂载两次：根路径保持原有兼容，/api 前缀供前端（同源部署/预览）调用
app.include_router(router)
app.include_router(router, prefix="/api")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """SPA 兜底：优先返回 dist 内真实文件（js/css/图片），其余路径回 index.html。"""
    if full_path:
        candidate = (_frontend_dist / full_path).resolve()
        if candidate.is_file() and _frontend_dist.resolve() in candidate.parents:
            return FileResponse(candidate)
    index = _frontend_dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="frontend not built; run `npm run build` in frontend/")
