from fastapi import FastAPI

from backend.app.api.sprint_planning import router as sprint_planning_router
from backend.app.api.intelligence import router as intelligence_router


app = FastAPI(
    title="AI Sprint Planning Assistant",
    version="0.1.0",
)


app.include_router(sprint_planning_router)
app.include_router(intelligence_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai-sprint-planner",
    }
