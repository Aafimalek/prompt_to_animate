from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import numpy as np


@dataclass
class RewardFeatures:
    static_error_count: int
    visual_score: float
    pacing_seconds: float
    target_seconds_min: float
    target_seconds_max: float
    render_cost_estimate: float
    memory_similarity: float


@dataclass
class RewardComponents:
    static_component: float
    visual_component: float
    pacing_component: float
    cost_component: float
    memory_component: float

    def as_vector(self) -> np.ndarray:
        return np.array(
            [
                self.static_component,
                self.visual_component,
                self.pacing_component,
                self.cost_component,
                self.memory_component,
            ],
            dtype=float,
        )


@dataclass
class RewardWeights:
    static_weight: float = 0.35
    visual_weight: float = 0.25
    pacing_weight: float = 0.20
    cost_weight: float = 0.10
    memory_weight: float = 0.10
    bias: float = 0.0

    def normalized(self) -> "RewardWeights":
        total = (
            self.static_weight
            + self.visual_weight
            + self.pacing_weight
            + self.cost_weight
            + self.memory_weight
        )
        if total <= 0:
            return RewardWeights()
        return RewardWeights(
            static_weight=self.static_weight / total,
            visual_weight=self.visual_weight / total,
            pacing_weight=self.pacing_weight / total,
            cost_weight=self.cost_weight / total,
            memory_weight=self.memory_weight / total,
            bias=self.bias,
        )

    def to_dict(self) -> dict:
        return {
            "static_weight": float(self.static_weight),
            "visual_weight": float(self.visual_weight),
            "pacing_weight": float(self.pacing_weight),
            "cost_weight": float(self.cost_weight),
            "memory_weight": float(self.memory_weight),
            "bias": float(self.bias),
        }

    @staticmethod
    def from_dict(payload: dict) -> "RewardWeights":
        try:
            return RewardWeights(
                static_weight=float(payload.get("static_weight", 0.35)),
                visual_weight=float(payload.get("visual_weight", 0.25)),
                pacing_weight=float(payload.get("pacing_weight", 0.20)),
                cost_weight=float(payload.get("cost_weight", 0.10)),
                memory_weight=float(payload.get("memory_weight", 0.10)),
                bias=float(payload.get("bias", 0.0)),
            ).normalized()
        except Exception:
            return RewardWeights()


def _duration_fit_score(pacing_seconds: float, target_min: float, target_max: float) -> float:
    if pacing_seconds <= 0:
        return 0.0
    if target_min <= pacing_seconds <= target_max:
        return 1.0
    if pacing_seconds < target_min:
        gap = target_min - pacing_seconds
    else:
        gap = pacing_seconds - target_max
    denom = max(1.0, (target_max - target_min))
    normalized = min(1.0, gap / denom)
    return max(0.0, 1.0 - normalized)


def compute_reward_components(features: RewardFeatures) -> RewardComponents:
    static_component = max(0.0, 1.0 - (features.static_error_count * 0.25))
    visual_component = max(0.0, min(1.0, features.visual_score / 100.0))
    pacing_component = _duration_fit_score(
        features.pacing_seconds,
        features.target_seconds_min,
        features.target_seconds_max,
    )
    cost_component = max(0.0, 1.0 - min(1.0, features.render_cost_estimate))
    memory_component = max(0.0, min(1.0, features.memory_similarity))
    return RewardComponents(
        static_component=static_component,
        visual_component=visual_component,
        pacing_component=pacing_component,
        cost_component=cost_component,
        memory_component=memory_component,
    )


def _default_weights_path() -> Path:
    raw = (os.environ.get("MANIM_REWARD_WEIGHTS_PATH") or "").strip()
    if raw:
        return Path(raw).resolve()
    return (Path(__file__).resolve().parent / "benchmarks" / "reward_weights.json").resolve()


def load_reward_weights(path: Path | None = None) -> RewardWeights:
    weights_path = (path or _default_weights_path()).resolve()
    if not weights_path.exists():
        return RewardWeights()
    try:
        payload = json.loads(weights_path.read_text(encoding="utf-8"))
    except Exception:
        return RewardWeights()
    if not isinstance(payload, dict):
        return RewardWeights()
    return RewardWeights.from_dict(payload)


def save_reward_weights(weights: RewardWeights, path: Path | None = None) -> Path:
    weights_path = (path or _default_weights_path()).resolve()
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.write_text(json.dumps(weights.to_dict(), indent=2), encoding="utf-8")
    return weights_path


def score_generation_candidate(
    features: RewardFeatures,
    weights: RewardWeights | None = None,
) -> float:
    components = compute_reward_components(features)
    active_weights = (weights or load_reward_weights()).normalized()
    raw = (
        components.static_component * active_weights.static_weight
        + components.visual_component * active_weights.visual_weight
        + components.pacing_component * active_weights.pacing_weight
        + components.cost_component * active_weights.cost_weight
        + components.memory_component * active_weights.memory_weight
        + active_weights.bias
    )
    return round(max(0.0, min(100.0, raw * 100.0)), 2)


def train_reward_weights(
    component_rows: Iterable[RewardComponents],
    target_scores: Iterable[float],
) -> RewardWeights:
    rows = list(component_rows)
    targets = list(target_scores)
    if len(rows) < 6 or len(rows) != len(targets):
        return RewardWeights()

    x = np.vstack([row.as_vector() for row in rows])
    y = np.array([max(0.0, min(1.0, float(t))) for t in targets], dtype=float)

    # Add bias column.
    x_aug = np.hstack([x, np.ones((x.shape[0], 1), dtype=float)])
    try:
        beta, *_ = np.linalg.lstsq(x_aug, y, rcond=None)
    except Exception:
        return RewardWeights()

    weights = RewardWeights(
        static_weight=float(beta[0]),
        visual_weight=float(beta[1]),
        pacing_weight=float(beta[2]),
        cost_weight=float(beta[3]),
        memory_weight=float(beta[4]),
        bias=float(beta[5]),
    ).normalized()
    return weights

