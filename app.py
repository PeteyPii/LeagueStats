import asyncio
import contextlib
import logging

import fastapi
import uvicorn
from fastapi import responses

import notifiarr
import settings
from routers import summoner, update_matches

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(_: fastapi.FastAPI):
    # logging.getLogger().setLevel(logging.INFO)

    settings.apply_global_settings()

    update_matches_task = asyncio.create_task(update_matches.update_matches_loop())
    yield
    update_matches_task.cancel()


app = fastapi.FastAPI(lifespan=lifespan)

app.include_router(summoner.router)
app.include_router(update_matches.router)


@app.middleware("http")
async def exception_handling_middleware(request: fastapi.Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception("Internal server error", exc_info=e)
        notifiarr.send_notification(
            event="LeagueStats",
            title="Server Error",
            body=str(e),
            color="FF0000",
            **settings.notifiarr_settings(),
        )
        return responses.JSONResponse(content="Internal server error", status_code=500)


if __name__ == "__main__":
    settings.apply_global_settings()
    uvicorn.run(app, host="localhost", port=8000)
