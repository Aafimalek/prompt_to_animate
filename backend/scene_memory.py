from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

from .database import get_database


_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    tokens = [item for item in _TOKEN_SPLIT.split((text or "").lower()) if item]
    return set(tokens)


def _jaccard_similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta.intersection(tb))
    union = len(ta.union(tb))
    if union == 0:
        return 0.0
    return inter / union


async def get_scene_memory_collection():
    db = await get_database()
    return db["scene_memory"]


async def get_quality_feedback_collection():
    db = await get_database()
    return db["quality_feedback"]


async def retrieve_scene_memories(prompt: str, top_k: int = 3) -> List[Dict[str, Any]]:
    collection = await get_scene_memory_collection()
    candidates = await collection.find({}).sort("quality_score", -1).limit(120).to_list(length=120)
    ranked: List[Dict[str, Any]] = []
    for item in candidates:
        score = _jaccard_similarity(prompt, str(item.get("prompt", "")))
        if score <= 0:
            continue
        ranked.append(
            {
                "memory_id": str(item.get("_id", "")),
                "similarity": score,
                "prompt": item.get("prompt", ""),
                "scene_plan": item.get("scene_plan", {}),
                "style_pack": item.get("style_pack", "classic_clean"),
                "quality_score": float(item.get("quality_score", 0.0)),
                "lessons": item.get("lessons", []),
            }
        )
    ranked.sort(key=lambda row: (row["similarity"], row["quality_score"]), reverse=True)
    return ranked[: max(0, int(top_k))]


def format_memory_context(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return "No relevant historical scenes."
    lines: List[str] = []
    for idx, memory in enumerate(memories, start=1):
        prompt = str(memory.get("prompt", "")).strip()
        style_pack = str(memory.get("style_pack", "classic_clean"))
        quality = float(memory.get("quality_score", 0.0))
        lessons = memory.get("lessons", [])
        lesson_text = ", ".join(str(item) for item in lessons[:3]) if isinstance(lessons, list) else ""
        lines.append(
            f"{idx}. prompt='{prompt[:120]}' style={style_pack} quality={quality:.1f} lessons={lesson_text}"
        )
    return "\n".join(lines)


async def store_scene_memory(
    prompt: str,
    length: str,
    scene_plan: Dict[str, Any],
    code: str,
    quality_score: float,
    style_pack: str,
    lessons: List[str] | None = None,
    chat_id: str | None = None,
) -> str:
    collection = await get_scene_memory_collection()
    doc = {
        "prompt": prompt,
        "length": length,
        "scene_plan": scene_plan,
        "code": code,
        "style_pack": style_pack,
        "quality_score": float(quality_score),
        "lessons": list(lessons or []),
        "chat_id": chat_id or "",
        "created_at": datetime.utcnow(),
    }
    result = await collection.insert_one(doc)
    return str(result.inserted_id)


async def record_quality_feedback(
    chat_id: str,
    clerk_id: str,
    rating: int,
    note: str = "",
) -> str:
    collection = await get_quality_feedback_collection()
    sanitized_rating = max(1, min(5, int(rating)))
    result = await collection.insert_one(
        {
            "chat_id": chat_id,
            "clerk_id": clerk_id,
            "rating": sanitized_rating,
            "note": note.strip(),
            "created_at": datetime.utcnow(),
        }
    )
    return str(result.inserted_id)

