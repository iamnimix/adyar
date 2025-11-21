from fastapi import FastAPI

from backend.routes import falai
from backend.db.database import init_models


app = FastAPI()

app.include_router(falai.router)


@app.on_event("startup")
async def startup_event():

    await init_models()