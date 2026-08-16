from fastapi import APIRouter, HTTPException

from backend.app.intelligence.story_intelligence import StoryIntelligence
from backend.app.intelligence.duplicate_detector import DuplicateDetector


router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["Story Intelligence"],
)

intelligence = StoryIntelligence()
duplicate_detector = DuplicateDetector()


@router.post("/story/analyze")
def analyze_story(story: dict):
    return intelligence.analyze(story)


@router.post("/stories/analyze")
def analyze_stories(payload: dict):
    stories = payload.get("stories", [])

    if not isinstance(stories, list):
        raise HTTPException(
            status_code=400,
            detail="'stories' must be a list",
        )

    return {
        "stories": intelligence.analyze_many(stories)
    }


@router.post("/stories/similar")
def detect_similar_stories(payload: dict):
    stories = payload.get("stories", [])

    if not isinstance(stories, list):
        raise HTTPException(
            status_code=400,
            detail="'stories' must be a list",
        )

    return duplicate_detector.detect(stories)
