import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.logging import configure_logging
from app.dependencies import init_background_services, shutdown_background_services
from app.routers import agent, audio, health, spatial, vision
from app.websocket import dashboard, probe


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="SpatialVCS API",
        description=(
            "Spatial Version Control System — Search reality like the web, "
            "manage space like code. Built on Gemini Toolkit with Vision, Audio, and Spatial AI."
        ),
        version="2.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router_module in (health, vision, audio, agent, spatial, probe, dashboard):
        app.include_router(router_module.router)

    @app.on_event("startup")
    async def startup_background_services():
        init_background_services()

    @app.on_event("shutdown")
    async def shutdown_background_workers():
        await shutdown_background_services()

    if os.path.exists("demo"):
        app.mount("/demo", StaticFiles(directory="demo", html=True), name="demo")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
