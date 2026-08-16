
import json
from pathlib import Path


CACHE_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "story_estimation_cache.json"
)


def _load():
    if not CACHE_FILE.exists():
        return {}

    try:
        return json.loads(
            CACHE_FILE.read_text()
        )
    except Exception:
        return {}


def _save(data):
    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CACHE_FILE.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
        )
    )


def get_cached(story_id, content_hash):
    cache = _load()

    item = cache.get(story_id)

    if not item:
        return None

    # Story changed since previous estimation.
    if item.get("content_hash") != content_hash:
        return None

    return item


def save_cached(
    story_id,
    content_hash,
    estimated_points,
    confidence,
    reason,
):
    cache = _load()

    cache[story_id] = {
        "content_hash": content_hash,
        "estimated_points": estimated_points,
        "confidence": confidence,
        "reason": reason,
    }

    _save(cache)


def cache_stats():
    cache = _load()

    return {
        "count": len(cache),
        "file": str(CACHE_FILE),
    }
