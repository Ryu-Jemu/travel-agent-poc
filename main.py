from contextlib import asynccontextmanager

from fastapi import FastAPI

from models.schemas import RecommendRequest, RecommendResponse
from agent.graph import graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Travel Agent PoC", version="0.1.0", lifespan=lifespan)


@app.post("/api/v1/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    initial_state = {"raw_request": request.model_dump()}
    result = await graph.ainvoke(initial_state)
    return result["response"]


@app.get("/health")
async def health():
    return {"status": "ok"}
