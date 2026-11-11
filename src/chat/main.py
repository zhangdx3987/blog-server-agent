from fastapi import FastAPI

from chat.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Blog Server Agent",
        description="提供模型调用、会话管理和工具执行能力",
        version="0.1.0"
    )

    app.state.settings = settings

    @app.get("/health/live", tags=["health"])
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()