from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .database import get_chats_collection, get_database
from .llm_service import get_length_profile
from .pacing import estimate_code_duration_seconds
from .reward_model import (
    RewardComponents,
    RewardFeatures,
    RewardWeights,
    compute_reward_components,
    save_reward_weights,
    train_reward_weights,
)


def _estimate_render_cost(code: str) -> float:
    lines = [line for line in (code or "").splitlines() if line.strip()]
    line_factor = min(1.0, len(lines) / 420.0)
    estimate = estimate_code_duration_seconds(code or "")
    animation_factor = min(1.0, estimate.play_calls / 140.0)
    return max(0.0, min(1.0, 0.55 * line_factor + 0.45 * animation_factor))


def _feedback_target(rating: float | None, quality_score: float) -> float:
    if rating is not None:
        return max(0.0, min(1.0, rating / 5.0))
    return max(0.0, min(1.0, quality_score / 100.0))


async def train_reward_model_from_mongo(
    limit: int = 500,
    output_path: Path | None = None,
) -> Dict[str, object]:
    chats_collection = await get_chats_collection()
    db = await get_database()
    feedback_collection = db["quality_feedback"]

    feedback_rows = await feedback_collection.find({}).to_list(length=max(1, limit * 2))
    rating_by_chat: Dict[str, float] = {}
    for row in feedback_rows:
        chat_id = str(row.get("chat_id", "")).strip()
        if not chat_id:
            continue
        try:
            rating = float(row.get("rating", 0))
        except (TypeError, ValueError):
            continue
        if rating <= 0:
            continue
        rating_by_chat[chat_id] = rating

    chats = await chats_collection.find({}).sort("created_at", -1).limit(limit).to_list(length=limit)
    components: List[RewardComponents] = []
    targets: List[float] = []
    for chat in chats:
        metadata = chat.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        quality_report = metadata.get("quality_report", {})
        if not isinstance(quality_report, dict):
            quality_report = {}
        quality_score = float(quality_report.get("score", 70.0) or 70.0)
        static_error_count = int(quality_report.get("error_count", 0) or 0)
        code = str(chat.get("code", "") or "")
        length = str(chat.get("length", "Medium (15s)") or "Medium (15s)")
        profile = get_length_profile(length)
        features = RewardFeatures(
            static_error_count=static_error_count,
            visual_score=quality_score,
            pacing_seconds=estimate_code_duration_seconds(code).total_seconds,
            target_seconds_min=float(profile.get("target_seconds_min", 0)),
            target_seconds_max=float(profile.get("target_seconds_max", 0)),
            render_cost_estimate=_estimate_render_cost(code),
            memory_similarity=0.0,
        )
        components.append(compute_reward_components(features))
        chat_id = str(chat.get("_id", ""))
        rating = rating_by_chat.get(chat_id)
        targets.append(_feedback_target(rating, quality_score))

    weights: RewardWeights = train_reward_weights(components, targets)
    saved_to = save_reward_weights(weights, path=output_path)
    return {
        "trained_samples": len(components),
        "weights": weights.to_dict(),
        "saved_to": str(saved_to),
    }

